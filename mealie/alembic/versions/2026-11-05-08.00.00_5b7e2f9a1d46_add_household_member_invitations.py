"""add household member invitations

Existing users can be invited to join another household of their group. A row is a pending invitation;
accepting, declining or revoking it deletes the row.

Revision ID: 5b7e2f9a1d46
Revises: c4a1d2e8f7b3
Create Date: 2026-11-05 08:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "5b7e2f9a1d46"
down_revision: str | None = "c4a1d2e8f7b3"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "household_member_invitations",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("invited_by_id", mealie.db.migration_types.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "user_id", name="household_member_invitation_key"),
    )
    op.create_index(op.f("ix_household_member_invitations_created_at"), "household_member_invitations", ["created_at"])
    op.create_index(
        op.f("ix_household_member_invitations_household_id"), "household_member_invitations", ["household_id"]
    )
    op.create_index(op.f("ix_household_member_invitations_user_id"), "household_member_invitations", ["user_id"])


def downgrade():
    op.drop_index(op.f("ix_household_member_invitations_user_id"), table_name="household_member_invitations")
    op.drop_index(op.f("ix_household_member_invitations_household_id"), table_name="household_member_invitations")
    op.drop_index(op.f("ix_household_member_invitations_created_at"), table_name="household_member_invitations")
    op.drop_table("household_member_invitations")
