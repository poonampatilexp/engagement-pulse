from datetime import datetime
import enum
import uuid
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from database import Base


class UserRole(str, enum.Enum):
    CONSULTANT = "consultant"
    CLIENT_VIEWER = "client_viewer"


class RiskSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskStatus(str, enum.Enum):
    OPEN = "open"
    MITIGATING = "mitigating"
    CLOSED = "closed"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


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
    # Projects belonging to this organisation
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="organisation",
        cascade="all, delete-orphan",
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
    csv_jobs: Mapped[list["CSVImportJob"]] = relationship(
        "CSVImportJob",
        back_populates="created_by",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="check_project_risk_score_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organisation_id: Mapped[int] = mapped_column(
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    risk_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
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
    organisation: Mapped["Organisation"] = relationship(
        "Organisation",
        back_populates="projects",
    )
    risks: Mapped[list["Risk"]] = relationship(
        "Risk",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    csv_jobs: Mapped[list["CSVImportJob"]] = relationship(
        "CSVImportJob",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name='{self.name}' risk_score={self.risk_score}>"


class Risk(Base):
    __tablename__ = "risks"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="check_risk_severity_valid",
        ),
        CheckConstraint(
            "status IN ('open', 'mitigating', 'closed')",
            name="check_risk_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="risks",
    )

    def __repr__(self) -> str:
        return f"<Risk id={self.id} title='{self.title}' severity='{self.severity}' status='{self.status}'>"


class SeverityWeight(Base):
    __tablename__ = "severity_weights"
    __table_args__ = (
        UniqueConstraint("severity", name="uq_severity_weights_severity"),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="check_severity_weight_valid",
        ),
        CheckConstraint(
            "weight > 0",
            name="check_severity_weight_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)

    # Synonyms for flexible key/name property access
    key = synonym("severity")
    name = synonym("severity")

    def __repr__(self) -> str:
        return f"<SeverityWeight id={self.id} severity='{self.severity}' weight={self.weight}>"


class StatusWeight(Base):
    __tablename__ = "status_weights"
    __table_args__ = (
        UniqueConstraint("status", name="uq_status_weights_status"),
        CheckConstraint(
            "status IN ('open', 'mitigating', 'closed')",
            name="check_status_weight_valid",
        ),
        CheckConstraint(
            "weight >= 0",
            name="check_status_weight_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)

    # Synonyms for flexible key/name property access
    key = synonym("status")
    name = synonym("status")

    def __repr__(self) -> str:
        return f"<StatusWeight id={self.id} status='{self.status}' weight={self.weight}>"


class CSVImportJob(Base):
    __tablename__ = "csv_import_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'failed')",
            name="check_csv_job_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=JobStatus.QUEUED.value,
        server_default=text("'queued'"),
        nullable=False,
        index=True,
    )
    total_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    processed_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    error_details: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default=text("'{}'::json"),
        nullable=False,
    )
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
    project: Mapped["Project"] = relationship("Project", back_populates="csv_jobs")
    created_by: Mapped["User"] = relationship("User", back_populates="csv_jobs")

    def __repr__(self) -> str:
        return f"<CSVImportJob id={self.id} status='{self.status}' filename='{self.filename}'>"

