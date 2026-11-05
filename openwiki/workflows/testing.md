---
type: workflow
title: Testing and Quality Checks
description: How Mealie's backend pytest suite, multitenant and route-permission tests, Vitest frontend tests and Playwright end-to-end tests are organized, configured and run locally and in CI.
tags: [testing, pytest, vitest, playwright, ci]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-d3e07196ef45f8d269ef5588
    resource: repo://.github/workflows/test-backend.yml
  - id: openwiki-source-d6885b4bee001112bdd6744a
    resource: repo://frontend/vitest.config.js
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-84bf33f849f2a7d08e3c094c
    resource: repo://Taskfile.yml
  - id: openwiki-source-f0a6e7dc03522b2682f88655
    resource: repo://tests/conftest.py
  - id: openwiki-source-b1e334e5c69a677d82d733b0
    resource: repo://tests/e2e/login.spec.ts
  - id: openwiki-source-859f98720585f4648f0f7b2e
    resource: repo://tests/e2e/playwright.config.ts
  - id: openwiki-source-d9e3a22e196ed4d86cc42057
    resource: repo://tests/fixtures/fixture_database.py
  - id: openwiki-source-6de70c035d249140be2d437a
    resource: repo://tests/fixtures/fixture_multitenant.py
  - id: openwiki-source-e739e2adb93363fef0aee564
    resource: repo://tests/integration_tests/test_route_permissions.py
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Testing and Quality Checks

## Commands

Use `task` wrappers (defined in `Taskfile.yml`) rather than raw tools:

| Command | What it does |
| --- | --- |
| `task py:test [-- args]` | `uv run pytest -n auto --dist loadfile`: parallel workers, one test file per worker in order |
| `task py:check` | format, Ruff lint, semgrep authz rules, mypy and tests |
| `task py:semgrep` | runs `.semgrep/authz.yml` rules against `mealie` and their tests in `.semgrep/authz.py` |
| `task ui:test` / `task ui:check` | frontend `pnpm test` / lint (`--max-warnings=0`) plus tests |
| `task e2e:*` | builds the e2e Docker image and runs Playwright |

CI runs backend lint and tests on both SQLite and PostgreSQL (matrix) with an OpenLDAP service for LDAP login tests (`.github/workflows/test-backend.yml`), plus separate frontend (`test-frontend.yml`) and E2E (`e2e.yml`) workflows.

## Backend pytest

Configuration is in `pyproject.toml`: tests under `tests/`, `test_*` files, and **every warning not explicitly ignored fails the test run** (`filterwarnings = ["error", ...]`).

### Bootstrap (`tests/conftest.py`)

Before importing the app, `conftest.py` sets `PRODUCTION=True`, `TESTING=True` and `ALLOW_SIGNUP=True` through a `MonkeyPatch` (so the SPA is not mounted, see [[app-lifecycle]]). Under pytest-xdist each worker gets its own data dir (`tests/.temp/<worker>`), and with PostgreSQL its own database (`<db>_<worker>`) because the backup-restore test drops every table. It then calls `init_db.main()` to migrate and seed the database (see [[database-and-migrations]]).

Key fixtures:

- `api_client` (session scope) is a `TestClient` whose `generate_session` dependency is overridden to a fresh `SessionLocal`.
- `isolate_session_cookies` (autouse) clears the client's cookie jar before and after every test; otherwise the session cookie from a prior login would silently authenticate requests meant to be anonymous.
- `global_cleanup` removes the temp directory at the end.
- `session` and `unfiltered_database` (`fixtures/fixture_database.py`) give direct repository access with no group/household scope.
- `fixtures/fixture_users.py` builds unique users and groups (`unique_user`, `unique_admin`, `h2_user` for a second household, `g2_user` for a second group, `unprivileged_user`, `user_tuple`, `admin_token`, `ldap_user`); each returns an Authorization header rather than relying on cookies.
- `fixtures/fixture_multitenant.py` provides `MultiTenant` with two users in different groups.

### Layout

- `tests/unit_tests/`: pure logic and service tests (config, security, SPA static files, ingredient parser, schema, repository and service tests, migration tests, code generation).
- `tests/integration_tests/`: API tests through `api_client` by domain (admin, user, recipe, public explorer, recipe migrations, category/tag tools, OpenAPI, SPA, validators).
- `tests/multitenant_tests/`: abstract `ABCMultiTenantTestCase` plus cases for categories, foods, tags, tools and units, asserting a user from another group sees nothing and same-named resources do not collide (see [[multi-tenancy]]).
- `tests/utils/`: factories, assertion helpers and the generated `api_routes` URL helpers (regenerate with `task dev:generate`, see [[schemas-and-codegen]]).

### Route permission guard

`tests/integration_tests/test_route_permissions.py` iterates the real app's routes and compares each route's declared `Perm` (via `RequirePermission`) against an explicit `EXPECTED_ROUTE_PERMISSIONS` table, so any change to who can call an endpoint shows up as a diff in review. Semgrep authz rules in `.semgrep/` provide a static complement.

## Frontend tests (Vitest)

`frontend/vitest.config.js` uses jsdom with globals, an `app/tests/setup.ts` setup file, Vue/VueUse/vue-i18n auto-imports, inlined Vuetify, and v8 coverage over `app/{lib,components,composables,layouts,pages}` (excluding generated API types and tests). Tests sit beside code: `app/composables/__tests__`, `app/middleware/__tests__`, `app/plugins/__tests__`, and component tests such as `DropZone.test.ts`. New components are expected to ship with tests (see [[frontend]]).

## End-to-end (Playwright)

`tests/e2e/` contains specs (`login.spec.ts`, `oidc-native.spec.ts`, `recipe-card.spec.ts`) run against `http://localhost:9000` in Chromium, sequentially (`fullyParallel: false`, one worker and two retries on CI). The tests target a built Docker image with supporting services defined in `tests/e2e/docker`, and exercise real password login, LDAP login (the LDAP user must not see admin settings) and native OIDC flows (see [[auth-and-security]]).
