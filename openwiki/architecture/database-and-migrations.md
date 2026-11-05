---
type: architecture
title: Database Models and Alembic Migrations
description: How Mealie configures SQLAlchemy for SQLite and PostgreSQL, organizes ORM models, runs Alembic migrations and post-migration data fixes at startup, and marks columns as filterable.
tags: [sqlalchemy, alembic, sqlite, postgres, migrations]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-dce58f119d86be38775d7903
    resource: repo://mealie/db/db_setup.py
  - id: openwiki-source-d72a495ee948ab155fbde140
    resource: repo://mealie/db/init_db.py
  - id: openwiki-source-0a586b355a17102f7f016cea
    resource: repo://mealie/db/models/_filterable_column.py
  - id: openwiki-source-ac03e50d50151aaee98b5ad6
    resource: repo://mealie/db/models/_model_base.py
  - id: openwiki-source-9de5a07bfcce48ff9932f22a
    resource: repo://mealie/db/models/_model_utils/guid.py
  - id: openwiki-source-b8c7f44255fe49fe0e12fe0a
    resource: repo://mealie/services/query_filter/builder.py
  - id: openwiki-source-84bf33f849f2a7d08e3c094c
    resource: repo://Taskfile.yml
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Database Models and Alembic Migrations

## Engine and sessions

`mealie/db/db_setup.py` builds a single module-level engine and `SessionLocal` (`autocommit=False`, `autoflush=False`, `pool_pre_ping=True`) from `settings.DB_URL`. SQLite connections get `check_same_thread=False`. `DB_ENGINE` is `sqlite` (default) or `postgres`, and `DB_URL` is derived from a `DB_PROVIDER` object on the settings.

Engine `connect` listeners tune SQLite: optional WAL journal mode when `SQLITE_MIGRATE_JOURNAL_WAL` is on (a persistent database setting), and, when `TESTING`, `synchronous=OFF` for speed. `generate_session` and `session_context` are described in [[backend-layers]].

## Model organization

ORM models live in `mealie/db/models/`, grouped by domain: `group/`, `household/` (cookbooks, meal plans, shopping lists, webhooks, invite tokens, recipe actions), `recipe/` (recipes, ingredients, instructions, tags, categories, tools, comments, timeline, nutrition), `users/`, and `server/` (tasks). Helpers in `_model_utils/` include a platform-independent `GUID` type (native `UUID` on PostgreSQL, `CHAR(32)` hex elsewhere), UTC datetime helpers, and `auto_init`, which populates ORM models and their relationships from Pydantic data.

All models derive from `SqlAlchemyBase` (`_model_base.py`), which supplies an integer `id`, indexed `created_at`, `update_at` (with an `updated_at` synonym), and a `normalize` helper that transliterates, strips punctuation (except quote characters reserved for literal searches), lowercases and caps at 255 characters. The normalized values back search columns; see [[search-and-filtering]].

### Filterable columns

`FilterableColumn[T]` (`_filterable_column.py`) is a drop-in for `Mapped[T]` that sets `info={"filterable": True}` on the column. The query filter builder only accepts columns carrying that flag and raises `NonFilterableValueError` otherwise, so sensitive fields (for example the household iCal secret token) are kept un-annotated to prevent probing through filter expressions.

## Startup initialization

`mealie/db/init_db.py:main()`, called from the app lifespan (see [[app-lifecycle]]):

1. Retries `SELECT 1` up to 10 times, one second apart, then raises `ConnectionError`.
2. Locates the Alembic config (`ALEMBIC_CONFIG_FILE` env var, else `mealie/alembic/alembic.ini`).
3. Compares the database's current heads with the script directory's heads (`db_is_at_head`); if behind, runs `alembic upgrade head` and sets a flag to run data fixes.
4. On PostgreSQL, ensures the `pg_trgm` extension exists (needed for fuzzy search and GIN text indices).
5. If users already exist, runs `fix_migration_data` and `fix_group_with_no_name` (only after a migration, each wrapped in `safe_try` so failures are logged rather than fatal). If no users exist, calls `init_db`, which creates the default group (`DEFAULT_GROUP`, "Home"), default household (`DEFAULT_HOUSEHOLD`, "Family") and the default admin user.

Data fixes in `mealie/db/fixes/` repair state that schema migrations alone cannot, for example `fix_dangling_refs` reassigns or deletes rows pointing at removed users per group.

## Writing migrations

Migrations are date-prefixed files in `mealie/alembic/versions/`. Generate one with `task py:migrate -- "description"`, which runs `alembic revision --autogenerate` and then formats the result. Because the project supports both SQLite and PostgreSQL, migrations must be checked on both. Schema changes also require updating Pydantic schemas and running code generation (see [[schemas-and-codegen]]). Backup restore, which replays data through the exporter, is covered in [[backups-and-migrations-import]].
