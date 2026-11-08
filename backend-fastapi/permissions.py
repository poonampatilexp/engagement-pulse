import os
import sys
from typing import Any

# Ensure backend-fastapi directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session
import models


def can_access_organisation(user: Any, organisation_id: int | None, db: Session | None = None) -> bool:
    """Check if a user is permitted to access (read) a specific organisation.

    - Consultants: permitted only for organisations assigned through consultant_organisation_access.
    - Client viewers: permitted only for their own assigned organisation_id.
    - Missing, inactive, or unassigned access is denied by default (returns False).
    """
    if not user or not getattr(user, "is_active", False) or organisation_id is None:
        return False

    role = getattr(user, "role", None)

    if role == models.UserRole.CLIENT_VIEWER.value:
        user_org_id = getattr(user, "organisation_id", None)
        return user_org_id is not None and user_org_id == organisation_id

    if role == models.UserRole.CONSULTANT.value:
        # Check through assigned_organisations relationship
        assigned = getattr(user, "assigned_organisations", None)
        if assigned is not None:
            try:
                return any(getattr(org, "id", None) == organisation_id for org in assigned)
            except Exception:
                pass

        # Fallback to direct query if db session is available
        session = db or object_session(user)
        if session is not None:
            access = session.execute(
                select(models.ConsultantOrganisationAccess).where(
                    models.ConsultantOrganisationAccess.user_id == getattr(user, "id", None),
                    models.ConsultantOrganisationAccess.organisation_id == organisation_id,
                )
            ).scalar_one_or_none()
            return access is not None

        return False

    return False


def can_edit_organisation(user: Any, organisation_id: int | None, db: Session | None = None) -> bool:
    """Check if a user is permitted to edit a specific organisation.

    - Consultants: permitted only for organisations assigned through consultant_organisation_access.
    - Client viewers: never permitted to edit (always False).
    - Missing, inactive, or unassigned access is denied by default (returns False).
    """
    if not user or not getattr(user, "is_active", False) or organisation_id is None:
        return False

    role = getattr(user, "role", None)

    if role == models.UserRole.CLIENT_VIEWER.value:
        return False

    if role == models.UserRole.CONSULTANT.value:
        return can_access_organisation(user, organisation_id, db=db)

    return False

