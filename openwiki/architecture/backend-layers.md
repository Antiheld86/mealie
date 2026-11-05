---
type: architecture
title: Backend Controller-Service-Repository Layers
description: How Mealie's FastAPI backend is layered into class-based controllers, services and group/household-scoped repositories, and how dependency injection, sessions and the HttpRepo mixin tie them together.
tags: [fastapi, controllers, repositories, dependency-injection, architecture]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-dce58f119d86be38775d7903
    resource: repo://mealie/db/db_setup.py
  - id: openwiki-source-f0be07a015fcc993f8713b66
    resource: repo://mealie/repos/all_repositories.py
  - id: openwiki-source-c98346f1ce528450feea0738
    resource: repo://mealie/repos/repository_factory.py
  - id: openwiki-source-0cc6582ff007cbc68d57ad95
    resource: repo://mealie/repos/repository_generic.py
  - id: openwiki-source-b1a66eb95071f4fe297c87f0
    resource: repo://mealie/routes/__init__.py
  - id: openwiki-source-926e40f83be846aa82bb48ae
    resource: repo://mealie/routes/_base/base_controllers.py
  - id: openwiki-source-bbb3a868685a5ae2f9f8f00c
    resource: repo://mealie/routes/_base/controller.py
  - id: openwiki-source-acc77392fa4468052d26b01f
    resource: repo://mealie/routes/_base/mixins.py
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Backend Controller-Service-Repository Layers

## Overview

A request flows: **router/controller** (HTTP concerns, auth, validation) → **service** (business logic, in `mealie/services/`) → **repository** (SQLAlchemy access, in `mealie/repos/`) → **ORM models** (see [[database-and-migrations]]). Pydantic schemas (see [[schemas-and-codegen]]) are the contract between layers: repositories take and return schemas, not ORM rows.

## Route registration

`mealie/routes/__init__.py` creates `router = APIRouter(prefix="/api")` and includes each domain router (app, auth, users, households, groups, recipe, organizers, shared, comments, parser, unit_and_foods, admin, validators, explore). `mealie/app.py` includes this router plus the media and utility routers (see [[app-lifecycle]]).

## Class-based controllers

`mealie/routes/_base/controller.py` provides the `@controller(router, *urls)` decorator, adapted from fastapi-utils. It turns a class into a class-based view: annotated class attributes using `Depends(...)` become constructor dependencies, and methods decorated with the router become endpoints that receive a DI-built instance as `self`. Attributes starting with `_` are excluded from the signature and default to `None`.

Base classes in `mealie/routes/_base/base_controllers.py`:

- `_BaseController` injects the DB `session` (`generate_session`), a translator and locale config. It lazily builds `repos` as `AllRepositories(session, group_id=self.group_id, household_id=self.household_id)`, and caches `logger`, `settings` and `folders`. By default both IDs are `NOT_SET`.
- `BasePublicController` is for unauthenticated routes. `BasePublicGroupExploreController` resolves a public group from the URL slug (`get_public_group`) and scopes repos to it; `BasePublicHouseholdExploreController` adds `cross_household_repos`, which has no household filter, so callers must filter by household preferences (`private_household`).
- `BaseUserController` depends on `get_current_user` and `get_integration_id` (see [[auth-and-security]]); its `group_id`/`household_id` come from the authenticated user, so every query is scoped to that user's group and household.
- `BaseAdminController` depends on `get_admin_user` and overrides `repos` to use `group_id=None, household_id=None`, giving unscoped access across all groups.
- `BaseCrudController` adds an `EventBusService` dependency and `publish_event` to dispatch domain events (see [[events-and-notifications]]).

## Repositories

`AllRepositories` (`mealie/repos/repository_factory.py`) is a factory holding the session and the `group_id`/`household_id` scope; each repository is exposed as a `cached_property` (recipes, users, shopping lists, meal plans, API tokens, etc.). `get_repositories(session, group_id=..., household_id=...)` in `all_repositories.py` is the public constructor; the `NOT_SET` sentinel distinguishes "caller forgot" from an explicit `None` (unscoped).

`RepositoryGeneric[Schema, Model]` (`repository_generic.py`) implements common CRUD, pagination, ordering and query-filter support, building queries with `schema.loader_options()` for eager loading. Scope is enforced by two subclasses whose constructors raise `ValueError` if `group_id` (and, for `HouseholdRepositoryGeneric`, `household_id`) is `NOT_SET`; `_filter_builder` then adds the group/household IDs to queries. See [[multi-tenancy]]. Specialized repositories (recipes, shopping lists, meals, foods, units, cookbooks, etc.) extend these. Search and filtering internals are in [[search-and-filtering]].

## HttpRepo mixin

`HttpRepo[C, R, U]` in `mealie/routes/_base/mixins.py` wraps a repository for controllers: `create_one`, `get_one`, `update_one`, `patch_one` and delete helpers. Missing rows become 404 via `not_found`; any exception triggers `handle_exception`, which logs, rolls back the session and maps `NoResultFound` → 404, `IntegrityError` → 409 (with a "already exists" message on unique violations for SQLite and PostgreSQL) and everything else → 400 with an `ErrorResponse`.

## Sessions

`generate_session` (`mealie/db/db_setup.py`) is a generator dependency for FastAPI requests only; outside a request use `session_context()`, which closes the session on exit. Services and scripts should not create sessions manually.
