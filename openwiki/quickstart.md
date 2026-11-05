---
type: "Reference"
title: "Mealie Quickstart"
openwiki_generated: true
sources:
  - id: openwiki-source-1e075575622e1a77a3dc46e6
    resource: repo://.github/pull_request_template.md
  - id: openwiki-source-8037e2358a2c4f9b2c722a11
    resource: repo://AGENTS.md
  - id: openwiki-source-3cf93211abde5de6c3170d3d
    resource: repo://mealie/app.py
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-84bf33f849f2a7d08e3c094c
    resource: repo://Taskfile.yml
generated: { by: "claude-code", at: "2026-11-04T19:38:26.692Z" }
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:38:26.692Z
---


# Mealie Quickstart

Mealie is a self-hosted recipe manager, meal planner and shopping list app. The backend is FastAPI on Python 3.14 (`requires-python >=3.14,<3.15`) with SQLAlchemy and Alembic over SQLite or PostgreSQL; the frontend is a Nuxt 4 / Vue 3 / TypeScript single-page app in `frontend/`. Documentation sources are in `docs/`.

## Topology

- **Development**: two processes. `task py` runs the API on port 9000; `task ui` runs the Nuxt dev server on port 3000, which proxies `/api` to the backend. CORS for `localhost:3000` is enabled only when not in production. `task dev:services` starts Postgres and Mailpit containers.
- **Production**: the frontend is statically generated and served by FastAPI's SPA module in a single container. See [[app-lifecycle]] and [[frontend]].

## Commands

Prefer `task` over invoking tools directly, and `uv run` for any Python command.

| Need | Command |
| --- | --- |
| Install everything | `task setup` |
| Backend / frontend dev servers | `task py` / `task ui` |
| Regenerate types, schema exports, locales, test route helpers | `task dev:generate` |
| New DB migration | `task py:migrate -- "description"` |
| Backend full validation | `task py:check` (format, lint, semgrep, mypy, tests) |
| Targeted backend tests | `task py:test -- -k name` |
| Frontend checks | `task ui:check` |
| Docs server | `task docs` |

## Hard rules

- Never hand-edit generated files: `frontend/app/lib/api/types/` and the `mealie/schema/*/__init__.py` exports. Change the Pydantic schema and run `task dev:generate` ([[schemas-and-codegen]]).
- Only edit the `en-US` locale files for new strings; other locales are managed by Crowdin.
- Keep the controller → service → repository layering; get repositories through dependency injection and never build sessions manually ([[backend-layers]]).
- Everything is scoped to a group and household; choose the repository scope deliberately ([[multi-tenancy]]).
- Use `get_app_settings()` for configuration, never construct `AppSettings` directly.
- Type hints are mandatory in Python; frontend code must pass strict TypeScript.

## Pull requests and commits

- **Title**: Conventional Commits, prefixed with `feat:`, `fix:`, `docs:`, `chore:` or `dev:` (the repo's recent history follows this, for example `fix: ...`, `chore(deps): ...`).
- **Release notes**: put user-facing changes in the PR description.
- **Template** (`.github/pull_request_template.md`): the "What this PR does / why", "Which issue(s) this PR fixes" (use `Fixes #123` so issues close) and "AI / LLM Assistance" sections are required; "Special notes" and "Testing" may be filled in or deleted. Undisclosed LLM use can delay or close a PR.
- **Release readiness**: Mealie releases on a regular automatic schedule, so every PR must be stable and complete, with tests for new features or regressions ([[testing]]).
- **Before opening**: run `task py:check` and `task ui:check`; if you changed Pydantic schemas, run `task dev:generate`; make sure migrations work on both SQLite and PostgreSQL ([[database-and-migrations]]). Draft PRs are optional.
- **Pre-commit hooks**: `task setup:py` runs `uv run pre-commit install`, which enforces Ruff formatting and linting on commit.
- **Reviews** focus on architecture and logic (layering, group/household scoping, type hints, generated files untouched, only `en-US` locale changes); formatting and linting are left to CI.
- The repo is also set up for VS Code dev containers.

## Where to look

| If you are working on... | Read |
| --- | --- |
| A new endpoint, controller base class, HttpRepo mixin, DI wiring | [[backend-layers]] |
| Startup, lifespan, settings, scheduled jobs, SPA serving | [[app-lifecycle]] |
| Login, LDAP/OIDC/reverse proxy, tokens, lockouts, API tokens | [[auth-and-security]] |
| Data isolation, permissions (`Perm`, `require`), households vs groups | [[multi-tenancy]] |
| ORM models, Alembic migrations, SQLite vs PostgreSQL behavior | [[database-and-migrations]] |
| Pydantic schemas, TypeScript types, `dev:generate` | [[schemas-and-codegen]] |
| Importing recipes from URLs, HTML, AI, ingredient parsing | [[recipe-import-and-scraping]] |
| Search, `queryFilter` strings, pagination, suggestions | [[search-and-filtering]] |
| Meal plans, random meals, iCal feed, shopping lists | [[meal-plans-and-shopping-lists]] |
| Events, Apprise notifiers, webhooks, email | [[events-and-notifications]] |
| Backups, restores, group exports, importing from other apps | [[backups-and-migrations-import]] |
| Vue components, API client classes, composables, axios, i18n | [[frontend]] |
| Writing or running tests, CI, e2e | [[testing]] |

## Typical change recipes

- **Add a field to a model**: update the ORM model (and mark it `FilterableColumn` only if safe to filter on), the Pydantic schemas, create an Alembic migration, run `task dev:generate`, and test on both SQLite and PostgreSQL.
- **Add an endpoint**: add a method on a controller deriving from the right base class, declare `require(Perm.X)` if it needs a permission and update the expected permissions table in the route permission test, then regenerate test route helpers.
- **Add a notifier-visible event**: extend `EventTypes`, the notifier options column and migration, and publish via `BaseCrudController.publish_event`.
- **Add a frontend feature**: follow the component folder naming rules, add an API client method on the matching class in `lib/api`, put shared state in a composable, and add tests next to new components.
