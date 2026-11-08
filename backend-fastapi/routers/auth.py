from fastapi import APIRouter, Depends, HTTPException, status
import jwt
from pydantic import BaseModel, ConfigDict, computed_field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
import models
from security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class OrganisationRef(BaseModel):
    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    organisation: OrganisationRef | None = None
    organisations: list[OrganisationRef] | None = None

    @computed_field
    @property
    def name(self) -> str:
        return self.email.split("@")[0].replace(".", " ").title()

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    user: UserResponse | None = None

    @computed_field
    @property
    def access(self) -> str:
        return self.access_token

    @computed_field
    @property
    def refresh(self) -> str | None:
        return self.refresh_token


class RefreshTokenRequest(BaseModel):
    refresh: str | None = None
    refresh_token: str | None = None

    def get_token(self) -> str:
        token = self.refresh or self.refresh_token
        if not token or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required",
            )
        return token.strip()


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None

    @computed_field
    @property
    def access(self) -> str:
        return self.access_token

    @computed_field
    @property
    def refresh(self) -> str | None:
        return self.refresh_token


class LogoutRequest(BaseModel):
    refresh: str | None = None
    refresh_token: str | None = None


def build_user_response(user: models.User, db: Session) -> UserResponse:
    org_ref = None
    orgs_ref = None
    if user.role == models.UserRole.CLIENT_VIEWER.value and user.organisation_id:
        org = db.execute(
            select(models.Organisation).where(models.Organisation.id == user.organisation_id)
        ).scalar_one_or_none()
        if org:
            org_ref = OrganisationRef.model_validate(org)
    elif user.role == models.UserRole.CONSULTANT.value:
        assigned = db.execute(
            select(models.Organisation)
            .join(
                models.ConsultantOrganisationAccess,
                models.ConsultantOrganisationAccess.organisation_id == models.Organisation.id,
            )
            .where(models.ConsultantOrganisationAccess.user_id == user.id)
            .order_by(models.Organisation.id)
        ).scalars().all()
        orgs_ref = [OrganisationRef.model_validate(o) for o in assigned]

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        organisation=org_ref,
        organisations=orgs_ref,
    )


@router.post("/login", response_model=TokenResponse)
@router.post("/login/", response_model=TokenResponse, include_in_schema=False)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(
        select(models.User).where(models.User.email == credentials.email)
    ).scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    user_resp = build_user_response(user, db)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "user": user_resp,
    }


@router.post("/refresh", response_model=RefreshTokenResponse)
@router.post("/refresh/", response_model=RefreshTokenResponse, include_in_schema=False)
def refresh_token_endpoint(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    raw_token = payload.get_token()

    try:
        decoded = decode_refresh_token(raw_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_val = decoded.get("sub") or decoded.get("user_id")
    try:
        user_id = int(user_id_val)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.execute(
        select(models.User).where(models.User.id == user_id)
    ).scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": new_refresh_token,
    }


@router.get("/me", response_model=UserResponse)
@router.get("/me/", response_model=UserResponse, include_in_schema=False)
def get_me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_user_response(current_user, db)


@router.post("/logout")
@router.post("/logout/", include_in_schema=False)
def logout(payload: LogoutRequest | None = None):
    return {"success": True}


class WebSocketTicketResponse(BaseModel):
    ticket: str
    expires_in: int = 30


@router.post(
    "/ws-ticket",
    response_model=WebSocketTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/ws-ticket/",
    response_model=WebSocketTicketResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def get_websocket_ticket(
    current_user: models.User = Depends(get_current_user),
):
    """Generates a short-lived single-use ticket for WebSocket authentication.
    
    Used by /ws/organisations/{org_id}/ to authenticate without exposing long-lived JWTs.
    """
    from ws_ticket_service import WebSocketTicketService

    ticket = WebSocketTicketService.create_ticket(current_user.id)
    return {
        "ticket": ticket,
        "expires_in": WebSocketTicketService.TICKET_TTL,
    }


