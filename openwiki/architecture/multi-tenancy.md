---
type: architecture
title: Groups, Households and Data Scoping
description: How Mealie isolates data between groups and households, how repositories and controllers enforce scope, the per-user permission flags and RequirePermission dependency, and the tests that guard tenant boundaries.
tags: [multi-tenancy, groups, households, permissions, authorization]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-53ef6db32a5f7b71a701e658
    resource: repo://mealie/db/models/household/household_to_recipe.py
  - id: openwiki-source-4bdae710f68afb8909d0c88c
    resource: repo://mealie/db/models/household/household.py
  - id: openwiki-source-46490f0407b0d71113fd8f14
    resource: repo://mealie/db/models/household/preferences.py
  - id: openwiki-source-995081425e60f1bd11f16879
    resource: repo://mealie/db/models/users/users.py
  - id: openwiki-source-0cc6582ff007cbc68d57ad95
    resource: repo://mealie/repos/repository_generic.py
  - id: openwiki-source-9c84cba8f2c7191a01de810d
    resource: repo://mealie/repos/repository_recipes.py
  - id: openwiki-source-68b952f45210ee55c054562e
    resource: repo://mealie/routes/_base/permissions.py
  - id: openwiki-source-e739e2adb93363fef0aee564
    resource: repo://tests/integration_tests/test_route_permissions.py
  - id: openwiki-source-450be704b9062415e2f7e6a5
    resource: repo://tests/multitenant_tests/case_abc.py
  - id: openwiki-source-294c726acd49fd5937cfc11d
    resource: repo://tests/multitenant_tests/test_multitenant_cases.py
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Groups, Households and Data Scoping

## Model

Mealie has two tenancy levels. A **group** is the top-level tenant; it contains one or more **households**. Households own meal plans, shopping lists, cookbooks, webhooks, notifiers, invite tokens and recipe actions, while recipes and organizers (tags, categories, tools, foods, units, labels) belong to the group. Households have unique `(group_id, name)` and `(group_id, slug)` constraints (`mealie/db/models/household/household.py`). Recipes are visible group-wide but tracked per household through the `households_to_recipes` association (for example `last_made`), and tools and foods "on hand" are many-to-many with households.

`HouseholdPreferencesModel` holds household policy flags such as `private_household` (default true: hides the household from public explore pages) and `lock_recipe_edits_from_other_households` (default true), plus a non-filterable `mealplan_ical_token`.

Users belong to a household (and through it, a group) and carry four permission flags: `can_manage`, `can_manage_household`, `can_invite` and `can_organize`, plus `admin`.

## Scoping in repositories

Scope is applied at the repository layer, not left to each route (see [[backend-layers]]):

- `AllRepositories` is created with `group_id` and `household_id`, each a UUID, `None` (unscoped) or the `NOT_SET` sentinel.
- Group-scoped repositories (`GroupRepositoryGeneric`) and household-scoped ones (`HouseholdRepositoryGeneric`) refuse to be constructed with `NOT_SET`, so forgetting to choose a scope fails loudly.
- `RepositoryGeneric._filter_builder` adds `group_id` / `household_id` equality to every `get_one`, `multi_query` and similar lookup when the repo has a scope.
- `_keep_scope` overwrites `group_id`/`household_id` in update payloads with the stored values, so an update cannot move a row to another tenant.
- `RepositoryRecipes` filters by `group_id` and, when set, `household_id`, and checks organizers against the repo's `group_id` when resolving them by ID.

Controller bases choose the scope: `BaseUserController` uses the logged-in user's group and household, `BaseAdminController` uses `None, None` for cross-tenant access, and public explore controllers use the group from the URL and only expose households whose preferences are not private (`get_public_household`, `cross_household_repos`). Callers that legitimately need to find a user before scope is known (login, token validation) call `get_repositories(session, group_id=None, household_id=None)` (see [[auth-and-security]]).

Because absent and inaccessible resources should look the same, `not_found` is used for both, while `forbidden` is for visible-but-not-allowed actions.

## Permissions

`mealie/routes/_base/permissions.py` defines `Perm` (`ANY_VALID_USER`, `GROUP_ORGANIZE`, `GROUP_MANAGE`, `GROUP_INVITE`, `HOUSEHOLD_MANAGE`), a table mapping each to the user flag that grants it, and `RequirePermission`, a route dependency that returns 403 with a translated message when the user lacks the flag. Routes declare it with `dependencies=[require(Perm.X)]`. Because the dependency instance stays on the route, `tests/integration_tests/test_route_permissions.py` can walk `app.routes` and compare against an explicit `EXPECTED_ROUTE_PERMISSIONS` table, so changing who can call a route is visible in review. Admin-only routes use `BaseAdminController` / `get_admin_user` instead.

## Tests

`tests/multitenant_tests/` defines an abstract `ABCMultiTenantTestCase` (seed data for a group, fetch via API, clean up) with concrete cases for categories, foods, tags, tools and units. `test_multitenant_cases.py` checks that a user from another group sees no data for each case and that same-named resources in different groups do not collide. See [[testing]].
