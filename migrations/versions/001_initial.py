"""initial FrameOps booking schema"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "booking_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("invitee_uri", sa.String(length=1000), nullable=True),
        sa.Column("event_uri", sa.String(length=1000), nullable=True),
        sa.Column("old_invitee_uri", sa.String(length=1000), nullable=True),
        sa.Column("new_invitee_uri", sa.String(length=1000), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("client_email", sa.String(length=320), nullable=True),
        sa.Column("scheduled_time", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("canceled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_booking_events_event_id","booking_events",["event_id"],unique=True)
    op.create_index("ix_booking_events_event_type","booking_events",["event_type"])
    op.create_index("ix_booking_events_invitee_uri","booking_events",["invitee_uri"])
    op.create_index("ix_booking_events_client_email","booking_events",["client_email"])
    op.create_table(
        "email_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("invitee_uri", sa.String(length=1000), nullable=True),
        sa.Column("event_uri", sa.String(length=1000), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dead_letter", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_id","kind",name="uq_email_outbox_event_kind"),
    )
    op.create_index("ix_email_outbox_event_id","email_outbox",["event_id"])
    op.create_index("ix_email_outbox_kind","email_outbox",["kind"])

def downgrade():
    op.drop_table("email_outbox")
    op.drop_table("booking_events")
