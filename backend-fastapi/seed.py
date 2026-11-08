import os
import sys

# Ensure backend-fastapi directory is in Python path for standalone executions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from config import settings
from database import SessionLocal
import models
from security import hash_password
from scoring_service import recalculate_project_score


def get_seed_passwords() -> tuple[str, str]:
    """Retrieve seed passwords from environment variables or settings.

    Defaults safely to standard development passwords if unspecified.
    """
    consultant_pw = (
        os.getenv("SEED_CONSULTANT_PASSWORD")
        or settings.SEED_CONSULTANT_PASSWORD
        or os.getenv("SEED_PASSWORD")
        or settings.SEED_PASSWORD
        or "ConsultantDevPass#2026"
    )
    viewer_pw = (
        os.getenv("SEED_CLIENT_VIEWER_PASSWORD")
        or settings.SEED_CLIENT_VIEWER_PASSWORD
        or os.getenv("SEED_PASSWORD")
        or settings.SEED_PASSWORD
        or "ViewerDevPass#2026"
    )

    return consultant_pw.strip(), viewer_pw.strip()


def seed():
    """Seed initial organisations, users, projects, and risks idempotently."""
    consultant_password, viewer_password = get_seed_passwords()

    with SessionLocal() as db:
        # 1. Organisations
        organisations_to_seed = [
            {"name": "Acme Health", "slug": "acme-health"},
            {"name": "Beta Care", "slug": "beta-care"},
            {"name": "Acme Corp", "slug": "acme-corp"},
            {"name": "Globex Corporation", "slug": "globex-corp"},
        ]

        seeded_orgs: dict[str, models.Organisation] = {}
        for org_info in organisations_to_seed:
            org = db.execute(
                select(models.Organisation).where(models.Organisation.slug == org_info["slug"])
            ).scalar_one_or_none()

            if not org:
                org = models.Organisation(name=org_info["name"], slug=org_info["slug"])
                db.add(org)
                db.flush()
                print(f"Created organisation: {org.name} ({org.slug})")
            else:
                print(f"Found existing organisation: {org.name} ({org.slug})")

            seeded_orgs[org_info["slug"]] = org

        acme_health_org = seeded_orgs["acme-health"]
        beta_care_org = seeded_orgs["beta-care"]
        acme_corp_org = seeded_orgs["acme-corp"]
        globex_org = seeded_orgs["globex-corp"]

        # 2. Consultant: assigned to all organisations
        consultant_email = "consultant@engagementpulse.com"
        consultant = db.execute(
            select(models.User).where(models.User.email == consultant_email)
        ).scalar_one_or_none()

        if not consultant:
            consultant = models.User(
                email=consultant_email,
                hashed_password=hash_password(consultant_password),
                role=models.UserRole.CONSULTANT.value,
                is_active=True,
                organisation_id=None,
            )
            db.add(consultant)
            db.flush()
            print(f"Created consultant user: {consultant.email}")
        else:
            print(f"Found existing consultant user: {consultant.email} (preserved existing password)")

        # Ensure consultant has access to all organisations
        for target_org in seeded_orgs.values():
            access = db.execute(
                select(models.ConsultantOrganisationAccess).where(
                    models.ConsultantOrganisationAccess.user_id == consultant.id,
                    models.ConsultantOrganisationAccess.organisation_id == target_org.id,
                )
            ).scalar_one_or_none()

            if not access:
                access = models.ConsultantOrganisationAccess(
                    user_id=consultant.id,
                    organisation_id=target_org.id,
                )
                db.add(access)
                db.flush()
                print(f"Assigned consultant {consultant.email} -> {target_org.name}")
            else:
                print(f"Assignment exists: {consultant.email} -> {target_org.name}")

        # 3. Client Viewers
        viewers_to_seed = [
            {"email": "viewer.acme@example.com", "org": acme_health_org},
            {"email": "viewer.beta@example.com", "org": beta_care_org},
            {"email": "viewer.globex@example.com", "org": globex_org},
        ]

        for viewer_info in viewers_to_seed:
            v_email = viewer_info["email"]
            v_org = viewer_info["org"]

            viewer = db.execute(
                select(models.User).where(models.User.email == v_email)
            ).scalar_one_or_none()

            if not viewer:
                viewer = models.User(
                    email=v_email,
                    hashed_password=hash_password(viewer_password),
                    role=models.UserRole.CLIENT_VIEWER.value,
                    is_active=True,
                    organisation_id=v_org.id,
                )
                db.add(viewer)
                db.flush()
                print(f"Created client viewer: {viewer.email} ({v_org.name})")
            else:
                print(f"Found existing client viewer: {viewer.email} (preserved existing password)")

        # 4. Sample Projects and Risks
        sample_projects = [
            {
                "org": acme_health_org,
                "name": "Patient Care Portal",
                "risks": [
                    {
                        "title": "Legacy Database Migration Delay",
                        "description": "Schema changes may delay production rollout.",
                        "severity": models.RiskSeverity.HIGH.value,
                        "status": models.RiskStatus.OPEN.value,
                        "owner": "Data Engineering Lead",
                    },
                    {
                        "title": "Third-party API Rate Limiting",
                        "description": "Integration partner experiencing throughput throttles.",
                        "severity": models.RiskSeverity.MEDIUM.value,
                        "status": models.RiskStatus.MITIGATING.value,
                        "owner": "Integration Team",
                    },
                ],
            },
            {
                "org": beta_care_org,
                "name": "Warehouse Automation",
                "risks": [
                    {
                        "title": "Security Audit Compliance Gap",
                        "description": "IAM roles require segregation of duties verification.",
                        "severity": models.RiskSeverity.CRITICAL.value,
                        "status": models.RiskStatus.OPEN.value,
                        "owner": "Security Architect",
                    },
                ],
            },
            {
                "org": globex_org,
                "name": "Cloud Infrastructure Migration",
                "risks": [
                    {
                        "title": "Security Audit Compliance Gap",
                        "description": "IAM roles require segregation of duties verification.",
                        "severity": models.RiskSeverity.CRITICAL.value,
                        "status": models.RiskStatus.OPEN.value,
                        "owner": "Security Architect",
                    },
                ],
            },
        ]

        for p_info in sample_projects:
            org = p_info["org"]
            project = db.execute(
                select(models.Project).where(
                    models.Project.organisation_id == org.id,
                    models.Project.name == p_info["name"],
                )
            ).scalar_one_or_none()

            if not project:
                project = models.Project(
                    organisation_id=org.id,
                    name=p_info["name"],
                    risk_score=0,
                )
                db.add(project)
                db.flush()
                print(f"Created sample project: '{project.name}' in {org.name}")

                for r_info in p_info["risks"]:
                    risk = models.Risk(
                        project_id=project.id,
                        title=r_info["title"],
                        description=r_info["description"],
                        severity=r_info["severity"],
                        status=r_info["status"],
                        owner=r_info["owner"],
                    )
                    db.add(risk)
                db.flush()

                try:
                    recalculate_project_score(db, project.id)
                except Exception as e:
                    print(f"Could not calculate score for project {project.id}: {e}")

        db.commit()
        print("Database seeding completed successfully.")


if __name__ == "__main__":
    seed()
