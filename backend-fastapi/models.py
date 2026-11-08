from datetime import datetime
import enum
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserRole(str, enum.Enum):
    CONSULTANT = "consultant"
    CLIENT_VIEWER = "client_viewer"


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    # Client viewers belong to exactly one organisation
    client_viewers: Mapped[list["User"]] = relationship(
        "User",
        back_populates="organisation",
        foreign_keys="User.organisation_id",
    )
    # Consultants access multiple organisations via association table
    consultants: Mapped[list["User"]] = relationship(
        "User",
        secondary="consultant_organisation_access",
        back_populates="assigned_organisations",
    )

    def __repr__(self) -> str:
        return f"<Organisation id={self.id} name='{self.name}'>"


class ConsultantOrganisationAccess(Base):
    __tablename__ = "consultant_organisation_access"
    __table_args__ = (
        UniqueConstraint("user_id", "organisation_id", name="uq_consultant_organisation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organisation_id: Mapped[int] = mapped_column(ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ConsultantOrganisationAccess user_id={self.user_id} organisation_id={self.organisation_id}>"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('consultant', 'client_viewer')",
            name="check_user_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # Client viewers belong to exactly one organisation
    organisation_id: Mapped[int | None] = mapped_column(
        ForeignKey("organisations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organisation: Mapped[Organisation | None] = relationship(
        "Organisation",
        back_populates="client_viewers",
        foreign_keys=[organisation_id],
    )
    assigned_organisations: Mapped[list[Organisation]] = relationship(
        "Organisation",
        secondary="consultant_organisation_access",
        back_populates="consultants",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"
