from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
import models
from permissions import can_access_organisation, can_edit_organisation

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectResponse(BaseModel):
    id: int
    name: str
    organisation_id: int
    risk_score: int

    model_config = ConfigDict(from_attributes=True)


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    organisation_id: int


class ProjectUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


@router.get("", response_model=list[ProjectResponse])
@router.get("/", response_model=list[ProjectResponse], include_in_schema=False)
def list_projects(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List only projects belonging to organisations the authenticated user may access.

    - Consultants: projects in assigned organisations.
    - Client viewers: projects in their own organisation.
    """
    if current_user.role == models.UserRole.CONSULTANT.value:
        projects = db.execute(
            select(models.Project)
            .join(
                models.ConsultantOrganisationAccess,
                models.ConsultantOrganisationAccess.organisation_id == models.Project.organisation_id,
            )
            .where(models.ConsultantOrganisationAccess.user_id == current_user.id)
            .order_by(models.Project.id)
        ).scalars().all()
    elif current_user.role == models.UserRole.CLIENT_VIEWER.value:
        if current_user.organisation_id is not None:
            projects = db.execute(
                select(models.Project)
                .where(models.Project.organisation_id == current_user.organisation_id)
                .order_by(models.Project.id)
            ).scalars().all()
        else:
            projects = []
    else:
        projects = []

    # Extra layer of defense enforcing organisation access
    return [p for p in projects if can_access_organisation(current_user, p.organisation_id, db=db)]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a project by ID only if the user has access to its organisation.

    Returns HTTP 404 for missing or inaccessible project IDs.
    """
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project or not can_access_organisation(current_user, project.organisation_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_project(
    payload: ProjectCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new project.

    - Only permitted if the user has edit permissions for the target organisation
      (consultant assigned to that organisation).
    - Returns HTTP 403 for forbidden writes.
    - risk_score cannot be directly set by clients; it initializes to 0.
    """
    if not can_edit_organisation(current_user, payload.organisation_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Not authorized to create projects in this organisation",
        )

    project = models.Project(
        name=payload.name.strip(),
        organisation_id=payload.organisation_id,
        risk_score=0,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update project name.

    - Returns HTTP 404 if project does not exist or user cannot access its organisation.
    - Returns HTTP 403 if user can access but is not permitted to edit (e.g. client viewer).
    - Does not allow direct modification of risk_score or organisation_id.
    """
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    # Inaccessible projects return 404 to preserve tenant privacy
    if not project or not can_access_organisation(current_user, project.organisation_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Forbidden write returns 403
    if not can_edit_organisation(current_user, project.organisation_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Not authorized to edit projects in this organisation",
        )

    project.name = payload.name.strip()
    db.commit()
    db.refresh(project)
    return project

