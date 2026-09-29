from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class Role:
    ORGANIZER = "organizer"
    JUDGE = "judge"
    PARTICIPANT = "participant"


class EventStatus:
    DRAFT = "draft"
    REGISTRATION = "registration"
    SUBMISSION = "submission"
    JUDGING = "judging"
    RESULTS = "results"
    CLOSED = "closed"
    ARCHIVED = "archived"
    ACTIVE = "active"


class ReviewStatus:
    DRAFT = "draft"
    FINALIZED = "finalized"
    LOCKED = "locked"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    organization: Mapped[str | None] = mapped_column(String(255))
    org_type: Mapped[str | None] = mapped_column(String(255))
    affiliation: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    specialization: Mapped[str | None] = mapped_column(String(255))
    college: Mapped[str | None] = mapped_column(String(255))
    degree: Mapped[str | None] = mapped_column(String(255))
    graduation_year: Mapped[str | None] = mapped_column(String(20))
    github_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organizer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    tagline: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    event_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    access_code: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default=EventStatus.REGISTRATION, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    registration_mode: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    editing_policy: Mapped[str] = mapped_column(String(64), default="allow-until-deadline", nullable=False)
    versioning_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_team_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_team_size: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    participant_capacity: Mapped[int | None] = mapped_column(Integer)
    judges_per_project: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    registration_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submission_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    judging_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tracks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    prizes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rubric: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    normalization_method: Mapped[str] = mapped_column(String(32), default="z_score", nullable=False)
    tie_break_order: Mapped[list] = mapped_column(JSON, default=lambda: ["normalized_score", "raw_score", "code_name"], nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="approved", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_membership_event_user"), Index("ix_membership_event_status", "event_id", "status"))


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    track: Mapped[str] = mapped_column(String(255), default="General", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class TeamMember(Base):
    __tablename__ = "team_members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_leader: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="Team Member", nullable=False)
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_user"), Index("ix_team_member_user", "user_id"))


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, unique=True)
    code_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    tagline: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    problem: Mapped[str] = mapped_column(Text, default="", nullable=False)
    solution: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tech_stack: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    github_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    demo_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    presentation_file_name: Mapped[str | None] = mapped_column(String(255))
    track: Mapped[str] = mapped_column(String(255), default="General", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="submitted", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ProjectVersion(Base):
    __tablename__ = "project_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="Submission update", nullable=False)
    edited_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (UniqueConstraint("project_id", "version", name="uq_project_version"),)


class JudgeAssignment(Base):
    __tablename__ = "judge_assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    judge_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="assigned", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint("project_id", "judge_id", name="uq_assignment_project_judge"),)


class JudgeConflict(Base):
    __tablename__ = "judge_conflicts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    judge_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    judge_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ReviewStatus.DRAFT, nullable=False)
    justification: Mapped[str] = mapped_column(Text, default="", nullable=False)
    total_raw: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint("project_id", "judge_id", name="uq_review_project_judge"),)


class ReviewCriterionScore(Base):
    __tablename__ = "review_criterion_scores"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)
    criterion_id: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    justification: Mapped[str] = mapped_column(Text, default="", nullable=False)
    __table_args__ = (UniqueConstraint("review_id", "criterion_id", name="uq_review_criterion"),)


class NormalizationSnapshot(Base):
    __tablename__ = "normalization_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    statistics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    results: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class Result(Base):
    __tablename__ = "results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    raw_score: Mapped[float] = mapped_column(Float, nullable=False)
    normalized_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("normalization_snapshots.id", ondelete="RESTRICT"), nullable=False, index=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (UniqueConstraint("snapshot_id", "project_id", name="uq_result_snapshot_project"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (Index("ix_audit_event_created", "event_id", "created_at"),)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
