"""judging hardening

Revision ID: 0002_judging_hardening
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_judging_hardening"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("events", sa.Column("tie_break_order", sa.JSON(), nullable=False, server_default='["normalized_score", "raw_score", "code_name"]'))

def downgrade():
    op.drop_column("events", "tie_break_order")
