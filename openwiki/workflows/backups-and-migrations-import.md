---
type: workflow
title: Backups, Exports and Third-Party Migrations
description: How admins create and restore full backups (database JSON plus data directory), how group recipe exports are written, and how migrators import recipes from other apps with per-run reports.
tags: [backup, restore, export, migration, import]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-622b14ef40aafb4ef7a3c88a
    resource: repo://mealie/routes/admin/admin_backups.py
  - id: openwiki-source-176578051fcdfae5b1c968f2
    resource: repo://mealie/routes/groups/controller_migrations.py
  - id: openwiki-source-11519f56de593803e56cecbc
    resource: repo://mealie/schema/group/group_migration.py
  - id: openwiki-source-a92a2d89e10bb67aaea6c2c8
    resource: repo://mealie/services/backups_v2/alchemy_exporter.py
  - id: openwiki-source-3c2004b33e313e89c0b37dd8
    resource: repo://mealie/services/backups_v2/backup_file.py
  - id: openwiki-source-59b4936ead340a28923d2832
    resource: repo://mealie/services/backups_v2/backup_v2.py
  - id: openwiki-source-c1e436254714b854b7cedff1
    resource: repo://mealie/services/exporter/_abc_exporter.py
  - id: openwiki-source-0207e3631274afe75dbf229f
    resource: repo://mealie/services/exporter/recipe_exporter.py
  - id: openwiki-source-8b6e8fc529364883c5d6b8dd
    resource: repo://mealie/services/migrations/_migration_base.py
  - id: openwiki-source-7b5aded946eb20373b413006
    resource: repo://mealie/services/scheduler/tasks/purge_group_exports.py
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Backups, Exports and Third-Party Migrations

Three separate mechanisms exist and should not be confused: **backups** (whole-instance, admin-only), **exports** (a group's recipes as a zip) and **migrations** (importing other apps' archives into the caller's group). Schema migrations of the database itself are in [[database-and-migrations]].

## Full backups (BackupV2)

Routes: `mealie/routes/admin/admin_backups.py` (`/backups`, `BaseAdminController`, so admin only; see [[backend-layers]]). Endpoints list backups and templates, create a backup, return a download token, delete, upload a `.zip`, and restore by file name. File names are resolved with a check that the path stays inside `BACKUP_DIR`, and uploads must be `.zip` files whose destination parent is the backup directory.

### Creating

`BackupV2.backup()` (`mealie/services/backups_v2/backup_v2.py`) names the file from the app version (`mealie_<version>_<timestamp>.zip`, or `dev-`/`nightly-` plus short commit hash), then writes a zip containing:

- `database.json`: every table dumped by `AlchemyExporter.dump()`, which first runs `fix_migration_data` (errors are logged and ignored) and then reflects all tables and serializes rows via `jsonable_encoder`;
- `data/...`: files from the data directory, excluding `mealie.db`, rotated `mealie.log*`, existing `.zip` files and anything under the `backups` or `.temp` directories.

### Restoring

`BackupV2.restore()`:

1. Opens the zip through `BackupFile`, which tolerates Safari-mangled archives with a `__MACOSX` directory and validates that both a `data` directory and `database.json` exist (otherwise `ValueError`).
2. For SQLite, first copies the live database to a dated `.bak.db` file in the data directory (PostgreSQL has no equivalent step).
3. Drops all tables (`drop_all`), then `AlchemyExporter.restore()` upgrades Alembic to the revision stored in the backup's `alembic_version` table, deletes and reinserts rows table by table with foreign keys disabled, converts column types back (names listed in `look_for_datetime`, `look_for_date`, `look_for_time` become datetimes/dates/times, and a test guards that new datetime columns are added), resets PostgreSQL sequences, disposes the engine, and calls `init_db.main()` so remaining migrations run.
4. Copies the data directory back, replacing each directory, but of loose files only restores `.secret`; then clears the `get_app_settings` cache so the restored secret takes effect.

Because the secret and database are replaced together, restoring a backup also restores the signing key for tokens (see [[auth-and-security]]).

## Group recipe exports

`ABCExporter` (`mealie/services/exporter/_abc_exporter.py`) is the base for exporters: subclasses yield `ExportedItem`s (a Pydantic model and a name) and a `destination_dir`; `export()` writes each as `<dir>/<name>/<name>.json` into a caller-owned zip and runs an optional post-export hook (for recipes, copying assets and images). `RecipeExporter` exports a list of recipe slugs for a group, and `Exporter.run` assembles exporters into a zip and returns a `GroupDataExport` record. Exports expire via the daily `purge_group_data_exports` task (see [[app-lifecycle]]).

## Third-party migrations

`POST /groups/migrations` (`mealie/routes/groups/controller_migrations.py`, `BaseUserController`) accepts a `migration_type` (`SupportedMigrations`: nextcloud, chowdown, copymethat, paprika, mealie_alpha, tandoor, plantoeat, myrecipebox, recipekeeper, cookn), an `add_migration_tag` flag and an archive. The upload is saved to a temporary zip path and a migrator class is looked up from a table keyed by type. The migrator receives the user's scoped repositories, session, user/household/group IDs and translator, and returns a `ReportSummary`.

Each importer subclasses `BaseMigrator` (`mealie/services/migrations/_migration_base.py`) and implements `_migrate()`, typically reading the archive and mapping foreign keys to Mealie fields with `MigrationAlias` entries (for example Paprika's `ingredients` → `recipeIngredient`). The shared base:

- creates a `Report` row (category migration, status in progress) before work starts, and after work sets status to success, failure or partial from the per-recipe `ReportEntry` results;
- `import_recipes_to_database` applies the household's default recipe settings, assigns the importing user and group, creates or reuses tags and categories (plus an optional tag named after the migrator), strips the source's `image` value, sanitizes IDs that could reference other groups' tools or sub-recipes, creates the recipe through `RecipeService`, rolls back the session on a failure and continues with the next recipe;
- handles oversize archives (`ArchiveTooLargeError`) by recording a failed entry instead of raising.

Recipe creation itself, including image handling, is described in [[recipe-import-and-scraping]].
