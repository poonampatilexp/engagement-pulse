from datetime import datetime
from typing import Any
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from csv_service import CSVImportJobService
from database import get_db
from dependencies import get_current_user
import models
from permissions import can_access_organisation

router = APIRouter(tags=["csv-jobs"])


class CSVImportJobResponse(BaseModel):
    id: str
    job_id: str
    project: int
    project_name: str
    filename: str
    status: str
    total_rows: int
    processed_rows: int
    error_details: dict[str, Any]
    created_by_email: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


def serialize_job(job: models.CSVImportJob) -> CSVImportJobResponse:
    return CSVImportJobResponse(
        id=str(job.id),
        job_id=str(job.id),
        project=job.project_id,
        project_name=job.project.name if job.project else "",
        filename=job.filename,
        status=job.status,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        error_details=job.error_details or {},
        created_by_email=job.created_by.email if job.created_by else "",
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post(
    "/projects/{project_id}/csv-jobs",
    response_model=CSVImportJobResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/projects/{project_id}/csv-jobs/",
    response_model=CSVImportJobResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/projects/{project_id}/import-csv",
    response_model=CSVImportJobResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/projects/{project_id}/import-csv/",
    response_model=CSVImportJobResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def upload_csv_job(
    project_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.CONSULTANT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only consultants can upload CSV imports.",
        )

    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project or not can_access_organisation(current_user, project.organisation_id, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied.",
        )

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are supported.",
        )

    content = file.file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded CSV file is empty.",
        )

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 10MB limit.",
        )

    job, _ = CSVImportJobService.create_import_job(
        db=db,
        user=current_user,
        project=project,
        file_content=content,
        filename=file.filename,
    )

    return serialize_job(job)


@router.get("/csv-jobs/{job_id}", response_model=CSVImportJobResponse)
@router.get("/csv-jobs/{job_id}/", response_model=CSVImportJobResponse, include_in_schema=False)
def get_csv_job_status(
    job_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.CONSULTANT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only consultants can view CSV import jobs.",
        )

    job = CSVImportJobService.get_job_for_user(db, current_user, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CSV import job not found or access denied.",
        )

    return serialize_job(job)


@router.get("/projects/{project_id}/csv-jobs", response_model=list[CSVImportJobResponse])
@router.get(
    "/projects/{project_id}/csv-jobs/",
    response_model=list[CSVImportJobResponse],
    include_in_schema=False,
)
def list_project_csv_jobs(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != models.UserRole.CONSULTANT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only consultants can view CSV import jobs.",
        )

    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project or not can_access_organisation(current_user, project.organisation_id, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied.",
        )

    jobs = CSVImportJobService.get_jobs_for_project(db, current_user, project_id)
    return [serialize_job(j) for j in jobs]

