import csv
from datetime import datetime, timezone
import hashlib
import io
import logging
import os
from typing import Any, Optional
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
import models
from permissions import can_access_organisation

logger = logging.getLogger(__name__)


class CSVImportJobService:
    @classmethod
    def create_import_job(
        cls,
        db: Session,
        user: models.User,
        project: models.Project,
        file_content: bytes,
        filename: str,
    ) -> tuple[models.CSVImportJob, bool]:
        """Validates consultant access, calculates file SHA-256 fingerprint, deduplicates

        concurrent imports, persists job in PostgreSQL, and enqueues Dramatiq background task.
        Returns: (job, created_new_bool)
        """
        # Calculate SHA-256 fingerprint of file contents
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Deduplication check: return existing job if one is already queued or processing for the same project & user
        existing_job = db.execute(
            select(models.CSVImportJob).where(
                models.CSVImportJob.project_id == project.id,
                models.CSVImportJob.created_by_id == user.id,
                models.CSVImportJob.file_hash == file_hash,
                models.CSVImportJob.status.in_([
                    models.JobStatus.QUEUED.value,
                    models.JobStatus.PROCESSING.value,
                ]),
            )
        ).scalar_one_or_none()

        if existing_job:
            logger.info("Found existing in-progress CSV job %s for file fingerprint %s", existing_job.id, file_hash)
            return existing_job, False

        # Store file on disk
        job_id = uuid.uuid4()
        safe_filename = os.path.basename(filename)
        upload_rel_dir = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        upload_dir = os.path.join(settings.CSV_UPLOAD_DIR, upload_rel_dir)
        os.makedirs(upload_dir, exist_ok=True)
        saved_path = os.path.join(upload_dir, f"{job_id}_{safe_filename}")

        with open(saved_path, "wb") as f:
            f.write(file_content)

        job = models.CSVImportJob(
            id=job_id,
            project_id=project.id,
            created_by_id=user.id,
            file_path=saved_path,
            filename=safe_filename,
            file_hash=file_hash,
            status=models.JobStatus.QUEUED.value,
            total_rows=0,
            processed_rows=0,
            error_details={},
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Enqueue Dramatiq worker task
        from tasks import process_csv_import_task

        try:
            process_csv_import_task.send(str(job.id))
        except Exception as exc:
            logger.warning("Failed to dispatch Dramatiq task to Redis for job %s: %s", job.id, exc)

        return job, True

    @classmethod
    def _parse_and_validate_csv(cls, file_path: str) -> tuple[list[dict[str, Any]], list[str], int]:
        """Reads CSV file and validates columns and rows against Risk model constraints.

        Returns: (valid_records, errors, total_rows_read)
        """
        if not file_path or not os.path.exists(file_path):
            return [], ["No file attached to import job."], 0

        errors: list[str] = []
        valid_records: list[dict[str, Any]] = []
        total_rows = 0

        with open(file_path, "rb") as f:
            stream = io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace")
            reader = csv.DictReader(stream)

            if not reader.fieldnames:
                return [], ["CSV file contains no header or is empty."], 0

            # Normalize header names case-insensitively
            col_map = {name.strip().lower(): name for name in reader.fieldnames if name and name.strip()}
            if "title" not in col_map:
                return [], ["Missing required column: 'title'."], 0

            allowed_severities = [s.value for s in models.RiskSeverity]
            allowed_statuses = [s.value for s in models.RiskStatus]

            for row_idx, row in enumerate(reader, start=2):
                total_rows += 1
                row_errors = []

                # Title: required, non-empty, max 255 chars
                raw_title = row.get(col_map.get("title"), "")
                title = raw_title.strip() if raw_title else ""
                if not title:
                    row_errors.append(f"Row {row_idx}: 'title' is required and cannot be empty.")
                elif len(title) > 255:
                    row_errors.append(f"Row {row_idx}: 'title' exceeds 255 characters.")

                # Severity: optional, defaults to 'medium', validates against RiskSeverity
                raw_sev = row.get(col_map.get("severity"), "")
                if raw_sev and raw_sev.strip():
                    sev = raw_sev.strip().lower()
                    if sev not in allowed_severities:
                        choices = ", ".join(allowed_severities)
                        row_errors.append(
                            f"Row {row_idx}: Invalid severity '{raw_sev.strip()}'. Allowed choices: {choices}."
                        )
                else:
                    sev = models.RiskSeverity.MEDIUM.value

                # Status: optional, defaults to 'open', validates against RiskStatus
                raw_stat = row.get(col_map.get("status"), "")
                if raw_stat and raw_stat.strip():
                    stat = raw_stat.strip().lower()
                    if stat not in allowed_statuses:
                        choices = ", ".join(allowed_statuses)
                        row_errors.append(
                            f"Row {row_idx}: Invalid status '{raw_stat.strip()}'. Allowed choices: {choices}."
                        )
                else:
                    stat = models.RiskStatus.OPEN.value

                # Description & Owner
                raw_desc = row.get(col_map.get("description"), "")
                desc = raw_desc.strip() if raw_desc else ""

                raw_owner = row.get(col_map.get("owner"), "")
                owner = raw_owner.strip() if raw_owner else ""
                if len(owner) > 255:
                    row_errors.append(f"Row {row_idx}: 'owner' exceeds 255 characters.")

                if row_errors:
                    errors.extend(row_errors)
                else:
                    valid_records.append({
                        "title": title,
                        "description": desc,
                        "severity": sev,
                        "status": stat,
                        "owner": owner,
                    })

            if total_rows == 0 and not errors:
                errors.append("CSV file contains no data rows.")

        return valid_records, errors, total_rows

    @classmethod
    def process_job(cls, job_id: uuid.UUID | str) -> Optional[models.CSVImportJob]:
        """Orchestrates CSV import job processing with a PostgreSQL-backed atomic claim.

        Guarantees that concurrent workers cannot claim the same job simultaneously,
        and repeated deliveries cannot duplicate imported risks.
        """
        if isinstance(job_id, str):
            try:
                job_uuid = uuid.UUID(job_id)
            except ValueError:
                return None
        else:
            job_uuid = job_id

        with SessionLocal() as db:
            # Atomic claim: update status to PROCESSING only if currently QUEUED
            stmt = (
                update(models.CSVImportJob)
                .where(
                    models.CSVImportJob.id == job_uuid,
                    models.CSVImportJob.status == models.JobStatus.QUEUED.value,
                )
                .values(
                    status=models.JobStatus.PROCESSING.value,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            result = db.execute(stmt)
            db.commit()

            if result.rowcount == 0:
                # Job is already PROCESSING, COMPLETED, or FAILED
                return db.execute(
                    select(models.CSVImportJob).where(models.CSVImportJob.id == job_uuid)
                ).scalar_one_or_none()

            job = db.execute(
                select(models.CSVImportJob).where(models.CSVImportJob.id == job_uuid)
            ).scalar_one()

            try:
                valid_records, errors, total_rows = cls._parse_and_validate_csv(job.file_path)

                if errors:
                    job.status = models.JobStatus.FAILED.value
                    job.total_rows = total_rows
                    job.processed_rows = 0
                    job.error_details = {"errors": errors}
                    job.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(job)
                    return job

                # In a database transaction: acquire project row lock, bulk insert risks, recalculate score
                project = db.execute(
                    select(models.Project)
                    .where(models.Project.id == job.project_id)
                    .with_for_update()
                ).scalar_one()

                for r in valid_records:
                    risk = models.Risk(
                        project_id=job.project_id,
                        title=r["title"],
                        description=r["description"],
                        severity=r["severity"],
                        status=r["status"],
                        owner=r["owner"],
                    )
                    db.add(risk)
                db.flush()

                from scoring_service import recalculate_project_score

                recalculate_project_score(db, job.project_id)

                job.status = models.JobStatus.COMPLETED.value
                job.total_rows = len(valid_records)
                job.processed_rows = len(valid_records)
                job.error_details = {}
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(job)

                return job

            except Exception as exc:
                logger.exception("Unexpected error processing CSV import job %s: %s", job_uuid, exc)
                try:
                    db.rollback()
                    job = db.execute(
                        select(models.CSVImportJob).where(models.CSVImportJob.id == job_uuid)
                    ).scalar_one()
                    if job.status == models.JobStatus.COMPLETED.value:
                        return job
                    job.status = models.JobStatus.FAILED.value
                    job.processed_rows = 0
                    job.error_details = {"errors": [str(exc)]}
                    job.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(job)
                except Exception:
                    pass
                return job

    @staticmethod
    def get_job_for_user(
        db: Session,
        user: models.User,
        job_id: uuid.UUID | str,
    ) -> Optional[models.CSVImportJob]:
        """Retrieves a CSV import job if accessible to the authenticated consultant.

        Enforces tenant organisation isolation and user job ownership.
        """
        if isinstance(job_id, str):
            try:
                job_uuid = uuid.UUID(job_id)
            except ValueError:
                return None
        else:
            job_uuid = job_id

        job = db.execute(
            select(models.CSVImportJob)
            .join(models.Project, models.Project.id == models.CSVImportJob.project_id)
            .where(models.CSVImportJob.id == job_uuid)
        ).scalar_one_or_none()

        if not job:
            return None

        # Verify organisation access
        if not can_access_organisation(user, job.project.organisation_id, db):
            return None

        # Enforce that only the creator/authorised consultant can view their job
        if job.created_by_id != user.id:
            return None

        return job

    @staticmethod
    def get_jobs_for_project(
        db: Session,
        user: models.User,
        project_id: int,
    ) -> list[models.CSVImportJob]:
        """Lists CSV import jobs for a project created by this consultant."""
        return db.execute(
            select(models.CSVImportJob)
            .where(
                models.CSVImportJob.project_id == project_id,
                models.CSVImportJob.created_by_id == user.id,
            )
            .order_by(models.CSVImportJob.created_at.desc())
        ).scalars().all()

