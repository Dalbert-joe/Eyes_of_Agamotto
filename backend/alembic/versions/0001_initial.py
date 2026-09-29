"""Initial AGAMOTTO PostgreSQL schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("organization", sa.String(255)), sa.Column("org_type", sa.String(255)),
        sa.Column("affiliation", sa.String(255)), sa.Column("title", sa.String(255)),
        sa.Column("specialization", sa.String(255)), sa.Column("college", sa.String(255)),
        sa.Column("degree", sa.String(255)), sa.Column("graduation_year", sa.String(20)),
        sa.Column("github_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("organizer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False), sa.Column("tagline", sa.String(500), nullable=False), sa.Column("description", sa.Text, nullable=False),
        sa.Column("event_code", sa.String(64), nullable=False), sa.Column("access_code", sa.String(128)), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("is_public", sa.Boolean, nullable=False), sa.Column("registration_mode", sa.String(32), nullable=False),
        sa.Column("editing_policy", sa.String(64), nullable=False), sa.Column("versioning_enabled", sa.Boolean, nullable=False),
        sa.Column("min_team_size", sa.Integer, nullable=False), sa.Column("max_team_size", sa.Integer, nullable=False),
        sa.Column("participant_capacity", sa.Integer), sa.Column("judges_per_project", sa.Integer, nullable=False),
        sa.Column("registration_start", sa.DateTime(timezone=True)), sa.Column("registration_deadline", sa.DateTime(timezone=True)),
        sa.Column("submission_deadline", sa.DateTime(timezone=True)), sa.Column("judging_deadline", sa.DateTime(timezone=True)),
        sa.Column("tracks", sa.JSON, nullable=False), sa.Column("prizes", sa.Text, nullable=False), sa.Column("rubric", sa.JSON, nullable=False),
        sa.Column("normalization_method", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_event_code", "events", ["event_code"], unique=True)
    op.create_index("ix_events_organizer_id", "events", ["organizer_id"])

    op.create_table("memberships", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("event_id", "user_id", name="uq_membership_event_user"))
    op.create_index("ix_membership_event_status", "memberships", ["event_id", "status"])

    op.create_table("teams", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("invite_code", sa.String(64), nullable=False), sa.Column("track", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("invite_code"))
    op.create_index("ix_teams_event_id", "teams", ["event_id"])

    op.create_table("team_members", sa.Column("id", sa.String(36), primary_key=True), sa.Column("team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("is_leader", sa.Boolean, nullable=False), sa.Column("role", sa.String(255), nullable=False), sa.UniqueConstraint("team_id", "user_id", name="uq_team_user"))
    op.create_index("ix_team_member_user", "team_members", ["user_id"])

    op.create_table("projects", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False), sa.Column("team_id", sa.String(36), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False), sa.Column("code_name", sa.String(255), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("tagline", sa.String(500), nullable=False), sa.Column("problem", sa.Text, nullable=False), sa.Column("solution", sa.Text, nullable=False), sa.Column("tech_stack", sa.JSON, nullable=False), sa.Column("github_url", sa.String(500), nullable=False), sa.Column("demo_url", sa.String(500), nullable=False), sa.Column("presentation_file_name", sa.String(255)), sa.Column("track", sa.String(255), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False), sa.Column("version", sa.Integer, nullable=False), sa.UniqueConstraint("team_id"), sa.UniqueConstraint("code_name"))
    op.create_index("ix_projects_event_id", "projects", ["event_id"])

    op.create_table("project_versions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("version", sa.Integer, nullable=False), sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False), sa.Column("summary", sa.Text, nullable=False), sa.Column("edited_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("snapshot", sa.JSON, nullable=False), sa.UniqueConstraint("project_id", "version", name="uq_project_version"))
    op.create_index("ix_project_versions_project_id", "project_versions", ["project_id"])

    op.create_table("judge_assignments", sa.Column("id", sa.String(36), primary_key=True), sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("judge_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("project_id", "judge_id", name="uq_assignment_project_judge"))

    op.create_table("judge_conflicts", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False), sa.Column("judge_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE")), sa.Column("reason", sa.Text, nullable=False), sa.Column("blocking", sa.Boolean, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))

    op.create_table("reviews", sa.Column("id", sa.String(36), primary_key=True), sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("judge_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("justification", sa.Text, nullable=False), sa.Column("total_raw", sa.Float, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("project_id", "judge_id", name="uq_review_project_judge"))
    op.create_table("review_criterion_scores", sa.Column("id", sa.String(36), primary_key=True), sa.Column("review_id", sa.String(36), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False), sa.Column("criterion_id", sa.String(128), nullable=False), sa.Column("score", sa.Float, nullable=False), sa.Column("justification", sa.Text, nullable=False), sa.UniqueConstraint("review_id", "criterion_id", name="uq_review_criterion"))

    op.create_table("normalization_snapshots", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False), sa.Column("method", sa.String(32), nullable=False), sa.Column("statistics", sa.JSON, nullable=False), sa.Column("results", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("results", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False), sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False), sa.Column("raw_score", sa.Float, nullable=False), sa.Column("normalized_score", sa.Float, nullable=False), sa.Column("final_score", sa.Float, nullable=False), sa.Column("rank", sa.Integer, nullable=False), sa.Column("snapshot_id", sa.String(36), sa.ForeignKey("normalization_snapshots.id", ondelete="RESTRICT"), nullable=False), sa.Column("published", sa.Boolean, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("snapshot_id", "project_id", name="uq_result_snapshot_project"))
    op.create_index("ix_results_snapshot_id", "results", ["snapshot_id"])

    op.create_table("audit_logs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE")), sa.Column("action", sa.String(100), nullable=False), sa.Column("entity_type", sa.String(100), nullable=False), sa.Column("entity_id", sa.String(100), nullable=False), sa.Column("details", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_audit_event_created", "audit_logs", ["event_id", "created_at"])

    op.create_table("notifications", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE")), sa.Column("message", sa.Text, nullable=False), sa.Column("read", sa.Boolean, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    for table in ["notifications", "audit_logs", "results", "normalization_snapshots", "review_criterion_scores", "reviews", "judge_conflicts", "judge_assignments", "project_versions", "projects", "team_members", "teams", "memberships", "events", "users"]:
        op.drop_table(table)
