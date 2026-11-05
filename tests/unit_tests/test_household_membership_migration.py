import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from tests.utils.alembic_reader import ALEMBIC_MIGRATIONS, import_file

GROUP = "a" * 32
HOUSEHOLD_1 = "b" * 32  # sorts first by name
HOUSEHOLD_2 = "c" * 32
MANAGER = "1" * 32
ADMIN = "2" * 32
MEMBER = "3" * 32
HOMELESS = "4" * 32


def _migration():
    path = next(ALEMBIC_MIGRATIONS.glob("*c4a1d2e8f7b3*.py"))
    return import_file("add_household_memberships", path)


def _run(connection: sa.Connection, fn) -> None:
    with Operations.context(MigrationContext.configure(connection)):
        fn()


def _create_legacy_schema(connection: sa.Connection) -> None:
    for statement in (
        "CREATE TABLE households (id CHAR(32) PRIMARY KEY, group_id CHAR(32), name VARCHAR)",
        "CREATE TABLE users (id CHAR(32) PRIMARY KEY, household_id CHAR(32) REFERENCES households (id), "
        "can_manage_household BOOLEAN, admin BOOLEAN)",
        "CREATE TABLE group_meal_plans (id INTEGER PRIMARY KEY, user_id CHAR(32) REFERENCES users (id))",
        "CREATE TABLE shopping_lists (id CHAR(32) PRIMARY KEY, group_id CHAR(32), "
        "user_id CHAR(32) NOT NULL REFERENCES users (id))",
        f"INSERT INTO households VALUES ('{HOUSEHOLD_1}', '{GROUP}', 'Alpha'), ('{HOUSEHOLD_2}', '{GROUP}', 'Beta')",
        "INSERT INTO users VALUES "
        f"('{MANAGER}', '{HOUSEHOLD_2}', 1, 0), ('{ADMIN}', '{HOUSEHOLD_1}', 0, 1), "
        f"('{MEMBER}', '{HOUSEHOLD_2}', 0, 0), ('{HOMELESS}', NULL, 0, 0)",
        f"INSERT INTO group_meal_plans VALUES (1, '{MANAGER}'), (2, '{MEMBER}'), (3, NULL)",
        f"INSERT INTO shopping_lists VALUES ('{'d' * 32}', '{GROUP}', '{MEMBER}'), "
        f"('{'e' * 32}', '{GROUP}', '{HOMELESS}')",
    ):
        connection.execute(sa.text(statement))


def test_household_membership_migration_round_trip() -> None:
    migration = _migration()
    engine = sa.create_engine("sqlite://")

    try:
        with engine.connect() as connection:
            _create_legacy_schema(connection)
            _run(connection, migration.upgrade)

            # every user with a household is a member of it; the old permission moved onto the membership
            memberships = {
                (row.user_id, row.household_id): bool(row.can_manage_household)
                for row in connection.execute(sa.text("SELECT * FROM households_to_users"))
            }
            assert memberships == {
                (MANAGER, HOUSEHOLD_2): True,
                (ADMIN, HOUSEHOLD_1): True,  # admins manage every household
                (MEMBER, HOUSEHOLD_2): False,
            }
            assert "can_manage_household" not in {c["name"] for c in sa.inspect(connection).get_columns("users")}

            # plans and lists keep the household they inherited from their owner
            plans = dict(connection.execute(sa.text("SELECT id, household_id FROM group_meal_plans")).all())
            assert plans == {1: HOUSEHOLD_2, 2: HOUSEHOLD_2, 3: None}  # ownerless plans have nothing to inherit
            lists = dict(connection.execute(sa.text("SELECT id, household_id FROM shopping_lists")).all())
            assert lists == {"d" * 32: HOUSEHOLD_2, "e" * 32: HOUSEHOLD_1}  # owner without a household -> first by name

            _run(connection, migration.downgrade)

            flags = dict(connection.execute(sa.text("SELECT id, can_manage_household FROM users")).all())
            assert flags == {MANAGER: True, ADMIN: True, MEMBER: False, HOMELESS: False}
            tables = sa.inspect(connection).get_table_names()
            assert "households_to_users" not in tables
            for table in ("group_meal_plans", "shopping_lists"):
                assert "household_id" not in {c["name"] for c in sa.inspect(connection).get_columns(table)}
    finally:
        engine.dispose()
