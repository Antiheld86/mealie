"""add household memberships and real household ids on meal plans and shopping lists

Users can now belong to several households. Their primary household stays `users.household_id`, and
`households_to_users` records every membership together with the per-household `can_manage_household`
permission (moved off the `users` table). Meal plans and shopping lists used to inherit their household from
the owning user; they now store it themselves so that it can be chosen per item.

Meal plan entries without an owner (`user_id IS NULL`) have no household to inherit and keep a NULL
`household_id`; they were never visible through household-scoped queries before and remain so.

Revision ID: c4a1d2e8f7b3
Revises: 071e03b4f851
Create Date: 2026-11-04 20:00:00.000000

"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types
from mealie.core.root_logger import get_logger
from mealie.db.models._model_utils.guid import GUID

# revision identifiers, used by Alembic.
revision = "c4a1d2e8f7b3"
down_revision: str | None = "071e03b4f851"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

logger = get_logger()


def new_id() -> str:
    return GUID.convert_value_to_guid(GUID.generate(), op.get_bind().dialect)  # type: ignore


def upgrade():
    conn = op.get_bind()

    # 1. membership table
    op.create_table(
        "households_to_users",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("user_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("can_manage_household", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "user_id", name="household_id_user_id_key"),
    )
    op.create_index(op.f("ix_households_to_users_created_at"), "households_to_users", ["created_at"], unique=False)
    op.create_index(op.f("ix_households_to_users_household_id"), "households_to_users", ["household_id"])
    op.create_index(op.f("ix_households_to_users_user_id"), "households_to_users", ["user_id"])

    # 2. one membership per existing user, for their primary household; admins manage every household
    memberships = sa.table(
        "households_to_users",
        sa.column("id", mealie.db.migration_types.GUID()),
        sa.column("household_id", mealie.db.migration_types.GUID()),
        sa.column("user_id", mealie.db.migration_types.GUID()),
        sa.column("can_manage_household", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
        sa.column("update_at", sa.DateTime()),
    )
    users = sa.table(
        "users",
        sa.column("id", mealie.db.migration_types.GUID()),
        sa.column("household_id", mealie.db.migration_types.GUID()),
        sa.column("can_manage_household", sa.Boolean()),
        sa.column("admin", sa.Boolean()),
    )
    rows = conn.execute(
        sa.select(users.c.id, users.c.household_id, users.c.can_manage_household, users.c.admin).where(
            users.c.household_id.is_not(None)
        )
    ).all()
    now = datetime.now(UTC).replace(tzinfo=None)
    if rows:
        op.bulk_insert(
            memberships,
            [
                {
                    "id": GUID.generate(),
                    "household_id": row.household_id,
                    "user_id": row.id,
                    "can_manage_household": bool(row.can_manage_household or row.admin),
                    "created_at": now,
                    "update_at": now,
                }
                for row in rows
            ],
        )

    # 3. real household columns on meal plans and shopping lists
    with op.batch_alter_table("group_meal_plans") as batch_op:
        batch_op.add_column(sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=True))
        batch_op.create_index(batch_op.f("ix_group_meal_plans_household_id"), ["household_id"], unique=False)
        batch_op.create_foreign_key("fk_group_meal_plans_household_id", "households", ["household_id"], ["id"])

    with op.batch_alter_table("shopping_lists") as batch_op:
        batch_op.add_column(sa.Column("household_id", mealie.db.migration_types.GUID(), nullable=True))
        batch_op.create_index(batch_op.f("ix_shopping_lists_household_id"), ["household_id"], unique=False)
        batch_op.create_foreign_key("fk_shopping_lists_household_id", "households", ["household_id"], ["id"])

    # 4. inherit the household from the owner, as before
    for table in ("group_meal_plans", "shopping_lists"):
        conn.execute(
            sa.text(
                f"UPDATE {table} SET household_id = "  # noqa: S608 - fixed table names
                f"(SELECT users.household_id FROM users WHERE users.id = {table}.user_id)"
            )
        )

    # lists whose owner has no household go to the first household (by name) of the list's group
    conn.execute(
        sa.text(
            "UPDATE shopping_lists SET household_id = ("
            "SELECT households.id FROM households WHERE households.group_id = shopping_lists.group_id "
            "ORDER BY households.name LIMIT 1) WHERE household_id IS NULL"
        )
    )
    orphaned = conn.execute(sa.text("SELECT COUNT(*) FROM shopping_lists WHERE household_id IS NULL")).scalar()
    if orphaned:
        logger.warning(f"Deleting {orphaned} shopping list(s) that belong to a group without any household")
        orphaned_items = (
            "(SELECT id FROM shopping_list_items WHERE shopping_list_id IN "
            "(SELECT id FROM shopping_lists WHERE household_id IS NULL))"
        )
        for item_child, item_column in (
            ("shopping_list_item_recipe_reference", "shopping_list_item_id"),
            ("shopping_list_item_extras", "shopping_list_item_id"),
        ):
            conn.execute(
                sa.text(f"DELETE FROM {item_child} WHERE {item_column} IN {orphaned_items}")  # noqa: S608
            )
        for child in (
            "shopping_list_items",
            "shopping_list_recipe_reference",
            "shopping_lists_multi_purpose_labels",
            "shopping_list_extras",
        ):
            conn.execute(
                sa.text(
                    f"DELETE FROM {child} WHERE shopping_list_id IN "  # noqa: S608 - fixed table names
                    "(SELECT id FROM shopping_lists WHERE household_id IS NULL)"
                )
            )
        conn.execute(sa.text("DELETE FROM shopping_lists WHERE household_id IS NULL"))

    with op.batch_alter_table("shopping_lists") as batch_op:
        batch_op.alter_column("household_id", existing_type=mealie.db.migration_types.GUID(), nullable=False)

    # 5. the household permission now lives on the membership
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("can_manage_household")


def downgrade():
    conn = op.get_bind()

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("can_manage_household", sa.Boolean(), nullable=True))

    conn.execute(
        sa.text(
            "UPDATE users SET can_manage_household = COALESCE(("
            "SELECT households_to_users.can_manage_household FROM households_to_users "
            "WHERE households_to_users.user_id = users.id "
            "AND households_to_users.household_id = users.household_id), FALSE)"
        )
    )

    with op.batch_alter_table("shopping_lists") as batch_op:
        batch_op.drop_constraint("fk_shopping_lists_household_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_shopping_lists_household_id"))
        batch_op.drop_column("household_id")

    with op.batch_alter_table("group_meal_plans") as batch_op:
        batch_op.drop_constraint("fk_group_meal_plans_household_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_group_meal_plans_household_id"))
        batch_op.drop_column("household_id")

    op.drop_index(op.f("ix_households_to_users_user_id"), table_name="households_to_users")
    op.drop_index(op.f("ix_households_to_users_household_id"), table_name="households_to_users")
    op.drop_index(op.f("ix_households_to_users_created_at"), table_name="households_to_users")
    op.drop_table("households_to_users")
