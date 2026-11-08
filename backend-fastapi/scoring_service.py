from sqlalchemy import select
from sqlalchemy.orm import Session

import models


class ScoringConfigurationError(RuntimeError):
    """Raised when scoring configuration (weights) is missing from the database."""
    pass


def recalculate_project_score(db: Session, project_id: int) -> int:
    """Recalculate project risk score from its risks and DB scoring weights.

    - Queries project with row lock (SELECT FOR UPDATE) to serialize concurrent updates.
    - Queries SeverityWeight and StatusWeight from PostgreSQL.
    - Each risk score = SeverityWeight * StatusWeight.
    - Project score = min(100, sum of risk scores).
    - If project has no risks, score is 0.
    - Updates project.risk_score in the current session.
    - Does NOT commit; the calling transaction owns the commit.
    - Raises ScoringConfigurationError if any required weight is missing in DB.
    """
    project = db.execute(
        select(models.Project).where(models.Project.id == project_id).with_for_update()
    ).scalar_one_or_none()

    if not project:
        raise ValueError(f"Project with id {project_id} not found")

    risks = db.execute(
        select(models.Risk).where(models.Risk.project_id == project_id)
    ).scalars().all()

    if not risks:
        project.risk_score = 0
        db.flush()
        return 0

    sev_weights = {
        sw.severity: sw.weight
        for sw in db.scalars(select(models.SeverityWeight)).all()
    }
    stat_weights = {
        sw.status: sw.weight
        for sw in db.scalars(select(models.StatusWeight)).all()
    }

    total_score = 0
    for risk in risks:
        if risk.severity not in sev_weights:
            raise ScoringConfigurationError(
                f"Missing scoring configuration for severity '{risk.severity}'"
            )
        if risk.status not in stat_weights:
            raise ScoringConfigurationError(
                f"Missing scoring configuration for status '{risk.status}'"
            )
        total_score += sev_weights[risk.severity] * stat_weights[risk.status]

    project_score = min(100, total_score)
    project.risk_score = project_score
    db.flush()
    return project_score

