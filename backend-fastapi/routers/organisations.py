from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
import models
from permissions import can_access_organisation
from routers.projects import ProjectResponse

router = APIRouter(prefix="/organisations", tags=["organisations"])


class OrganisationResponse(BaseModel):
    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[OrganisationResponse])
@router.get("/", response_model=list[OrganisationResponse], include_in_schema=False)
def list_organisations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve organisations accessible by the authenticated user.

    - Consultants: only organisations assigned via consultant_organisation_access.
    - Client viewers: only their single assigned organisation.
    """
    if current_user.role == models.UserRole.CONSULTANT.value:
        orgs = db.execute(
            select(models.Organisation)
            .join(
                models.ConsultantOrganisationAccess,
                models.ConsultantOrganisationAccess.organisation_id == models.Organisation.id,
            )
            .where(models.ConsultantOrganisationAccess.user_id == current_user.id)
            .order_by(models.Organisation.id)
        ).scalars().all()
    elif current_user.role == models.UserRole.CLIENT_VIEWER.value:
        if current_user.organisation_id is not None:
            org = db.execute(
                select(models.Organisation).where(
                    models.Organisation.id == current_user.organisation_id
                )
            ).scalar_one_or_none()
            orgs = [org] if org else []
        else:
            orgs = []
    else:
        orgs = []

    # Filter through organisation permission check
    return [org for org in orgs if can_access_organisation(current_user, org.id, db=db)]


@router.get("/{organisation_id}/projects", response_model=list[ProjectResponse])
@router.get("/{organisation_id}/projects/", response_model=list[ProjectResponse], include_in_schema=False)
def list_organisation_projects(
    organisation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve projects belonging to a specific organisation if accessible."""
    if not can_access_organisation(current_user, organisation_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organisation not found",
        )

    projects = db.execute(
        select(models.Project)
        .where(models.Project.organisation_id == organisation_id)
        .order_by(models.Project.id)
    ).scalars().all()
    return projects

