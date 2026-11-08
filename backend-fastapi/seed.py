import os
import sys

# Ensure backend-fastapi directory is in Python path for standalone executions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from config import settings
from database import SessionLocal
import models
from security import hash_password


def get_seed_passwords() -> tuple[str, str]:
    """Retrieve seed passwords from environment variables or settings.

    Fails safely without printing passwords if any required password is missing.
    """
    consultant_pw = (
        os.getenv("SEED_CONSULTANT_PASSWORD")
        or settings.SEED_CONSULTANT_PASSWORD
        or os.getenv("SEED_PASSWORD")
        or settings.SEED_PASSWORD
    )
    viewer_pw = (
        os.getenv("SEED_CLIENT_VIEWER_PASSWORD")
        or settings.SEED_CLIENT_VIEWER_PASSWORD
        or os.getenv("SEED_PASSWORD")
        or settings.SEED_PASSWORD
    )

    if not consultant_pw or not consultant_pw.strip():
        raise ValueError(
            "Missing SEED_CONSULTANT_PASSWORD. Please set SEED_CONSULTANT_PASSWORD "
            "(or SEED_PASSWORD) in your environment or .env file."
        )

    if not viewer_pw or not viewer_pw.strip():
        raise ValueError(
            "Missing SEED_CLIENT_VIEWER_PASSWORD. Please set SEED_CLIENT_VIEWER_PASSWORD "
            "(or SEED_PASSWORD) in your environment or .env file."
        )

    return consultant_pw.strip(), viewer_pw.strip()


def seed():
    """Seed initial organisations, consultant, and client viewers idempotently."""
    consultant_password, viewer_password = get_seed_passwords()

    with SessionLocal() as db:
        # 1. Organisations: Acme Health and Beta Care
        organisations_to_seed = [
            {"name": "Acme Health", "slug": "acme-health"},
            {"name": "Beta Care", "slug": "beta-care"},
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

        acme_org = seeded_orgs["acme-health"]
        beta_org = seeded_orgs["beta-care"]

        # 2. Consultant: assigned to both organisations
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

        # Ensure consultant has access to both organisations
        for target_org in [acme_org, beta_org]:
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

        # 3. Client Viewers: one belonging to each organisation
        viewers_to_seed = [
            {
                "email": "viewer.acme@example.com",
                "org": acme_org,
            },
            {
                "email": "viewer.beta@example.com",
                "org": beta_org,
            },
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

        db.commit()
        print("Database seeding completed successfully.")


if __name__ == "__main__":
    seed()

