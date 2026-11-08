from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, computed_field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
import models
from permissions import can_access_organisation, can_edit_organisation
from scoring_service import ScoringConfigurationError, recalculate_project_score
from broadcast_service import BroadcastService

router = APIRouter(tags=["risks"])


class RiskResponse(BaseModel):
    id: int
    project_id: int
    title: str
    description: str | None = None
    severity: models.RiskSeverity
    status: models.RiskStatus
    owner: str | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def project(self) -> int:
        return self.project_id

    model_config = ConfigDict(from_attributes=True)


class RiskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    severity: models.RiskSeverity = models.RiskSeverity.MEDIUM
    status: models.RiskStatus = models.RiskStatus.OPEN
    owner: str | None = Field(None, max_length=255)


class RiskUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    severity: models.RiskSeverity | None = None
    status: models.RiskStatus | None = None
    owner: str | None = Field(None, max_length=255)


@router.get("/projects/{project_id}/risks", response_model=list[RiskResponse])
@router.get("/projects/{project_id}/risks/", response_model=list[RiskResponse], include_in_schema=False)
def list_project_risks(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List risks for a project only if the user can access its organisation.

    Returns HTTP 404 for nonexistent or inaccessible projects.
    """
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id)
    ).scalar_one_or_none()

    if not project or not can_access_organisation(current_user, project.organisation_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    risks = db.execute(
        select(models.Risk).where(models.Risk.project_id == project_id).order_by(models.Risk.id)
    ).scalars().all()

    return risks


@router.post(
    "/projects/{project_id}/risks",
    response_model=RiskResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/projects/{project_id}/risks/",
    response_model=RiskResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_project_risk(
    project_id: int,
    payload: RiskCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a risk for a project in an assigned organisation.

    - Returns HTTP 404 if project does not exist or is in an inaccessible organisation.
    - Returns HTTP 403 if user cannot edit in the organisation (e.g. client viewer).
    - Cannot move or reassign the project_id.
    - Locks the project row (SELECT FOR UPDATE) to serialize concurrent updates.
    - Recalculates project risk score and commits in the same transaction.
    """
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id).with_for_update()
    ).scalar_one_or_none()

    if not project or not can_access_organisation(current_user, project.organisation_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not can_edit_organisation(current_user, project.organisation_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Not authorized to create risks in this organisation",
        )

    risk = models.Risk(
        project_id=project.id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description is not None else None,
        severity=payload.severity.value,
        status=payload.status.value,
        owner=payload.owner.strip() if payload.owner is not None else None,
    )
    db.add(risk)
    db.flush()

    try:
        recalculate_project_score(db, project.id)
    except ScoringConfigurationError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scoring configuration error: {e}",
        )

    db.commit()
    db.refresh(risk)

    BroadcastService.broadcast_data_changed(
        organisation_id=project.organisation_id,
        project_id=project.id,
        reason="risk_created",
    )

    return risk


@router.patch("/risks/{risk_id}", response_model=RiskResponse)
@router.patch("/risks/{risk_id}/", response_model=RiskResponse, include_in_schema=False)
def update_risk(
    risk_id: int,
    payload: RiskUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update title, description, severity, status, or owner for a risk.

    - Returns HTTP 404 if risk does not exist or user cannot access its project's organisation.
    - Returns HTTP 403 if user is not authorized to edit (e.g. client viewer).
    - Moving a risk to another project is not allowed.
    - Locks the project row (SELECT FOR UPDATE) to serialize concurrent updates.
    - Recalculates project risk score if severity or status changes and commits in the same transaction.
    """
    risk = db.execute(
        select(models.Risk).where(models.Risk.id == risk_id)
    ).scalar_one_or_none()

    if not risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found",
        )

    project = db.execute(
        select(models.Project).where(models.Project.id == risk.project_id).with_for_update()
    ).scalar_one_or_none()

    if not project or not can_access_organisation(current_user, project.organisation_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found",
        )

    if not can_edit_organisation(current_user, project.organisation_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Not authorized to edit risks in this organisation",
        )

    updated_fields = payload.model_dump(mode="json", exclude_unset=True)
    for field, value in updated_fields.items():
        setattr(risk, field, value.strip() if isinstance(value, str) else value)

    if "severity" in updated_fields or "status" in updated_fields:
        db.flush()
        try:
            recalculate_project_score(db, project.id)
        except ScoringConfigurationError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Scoring configuration error: {e}",
            )

    db.commit()
    db.refresh(risk)

    BroadcastService.broadcast_data_changed(
        organisation_id=project.organisation_id,
        project_id=project.id,
        reason="risk_updated",
    )

    return risk

