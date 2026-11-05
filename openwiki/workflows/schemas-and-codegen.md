---
type: workflow
title: Pydantic Schemas and Code Generation
description: How Mealie's Pydantic schemas (MealieModel and suffix conventions) feed generated TypeScript types, schema __init__ exports, locale files and pytest route helpers through the task dev:generate pipeline.
tags: [pydantic, codegen, typescript, schemas, workflow]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-f53f6b871cf80288a3e895fc
    resource: repo://dev/code-generation/gen_py_pytest_routes.py
  - id: openwiki-source-3892fc207b90f10e677e0dd7
    resource: repo://dev/code-generation/gen_py_schema_exports.py
  - id: openwiki-source-929b5946bc3a629ff92c47c8
    resource: repo://dev/code-generation/gen_ts_types.py
  - id: openwiki-source-9916080cf4a21a47e444adf4
    resource: repo://dev/code-generation/main.py
  - id: openwiki-source-e1f2263d50798f9f11e48da2
    resource: repo://dev/code-generation/utils/static.py
  - id: openwiki-source-115f79de3ec86f5a08097e0f
    resource: repo://mealie/schema/_mealie/mealie_model.py
  - id: openwiki-source-84bf33f849f2a7d08e3c094c
    resource: repo://Taskfile.yml
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Pydantic Schemas and Code Generation

## Schemas

Pydantic schemas live in `mealie/schema/<domain>/` (recipe, household, group, user, meal_plan, reports, response, openai, ...). They sit between the HTTP layer and the repositories (see [[backend-layers]]): controllers declare them as request bodies and `response_model`s, and repositories validate ORM rows into them.

Naming follows suffix conventions: `*Create` / `*In` for inputs, `*Update` for changes, `*Out` for responses, `*Save` for what is persisted after the server adds fields (for example `PlanRulesCreate` → `PlanRulesSave` adds `group_id`/`household_id` → `PlanRulesOut` adds `id`), and `*InDB`/`*Private*` variants for internal data with secrets.

### MealieModel

Most schemas extend `MealieModel` (`mealie/schema/_mealie/mealie_model.py`), which:

- sets `alias_generator=camelize` with `populate_by_name=True`, so the API speaks camelCase while Python uses snake_case;
- normalizes datetimes (fixing PostgreSQL's hour-only timezone offsets and adding UTC info);
- provides conversion helpers `cast` (copy matching fields into another model, with overrides), `map_to`, `map_from` and `merge`;
- exposes `loader_options()`, which repositories use to eager-load relationships, and search hooks (`_searchable_properties`, fuzzy vs tokenized `SearchType`) used by pagination search (see [[search-and-filtering]]);
- `UpdatedAtField` accepts several aliases for the database's `update_at` column.

## Generation pipeline

`task dev:generate` runs `uv run python dev/code-generation/main.py {{args}}` and then formats with Ruff. `main.py` registers named generators; with no arguments it runs all except the opt-in `crowdin-approvals` (which changes Crowdin rather than local files):

| Generator | Source | Output |
| --- | --- | --- |
| `schema` | classes in `mealie/schema/<pkg>/*.py` | the package's `__init__.py` re-exports and `__all__` |
| `types` | Pydantic models + global components | `frontend/app/lib/api/types/*.ts` and `frontend/app/types/components.d.ts` |
| `locales` | Crowdin / locale config | frontend locale lists (`use-locales/available-locales.ts`, plus the `MESSAGE_LOCALES` block in `nuxt.config.ts`) |
| `unit-systems` | unit definitions | `frontend/app/composables/recipes/unit-systems.ts` |
| `data-paths` | folders under `tests/data` | generated Python helpers for test data paths |
| `routes` | the app's OpenAPI | `tests/utils/api_routes/__init__.py` |

You can run a subset, for example `task dev:generate -- types`.

### Schema exports

`gen_py_schema_exports.py` scans each schema package, skips files starting with `_`, regex-extracts top-level `class` names from each file, sorts them, and renders `from .module import A, B` lines plus `__all__` into the package `__init__.py`. Those `__init__.py` files are therefore generated and must not be edited by hand; adding a class to a schema file requires regenerating them.

### TypeScript types

`gen_ts_types.py` imports every schema package (ignoring `static` and `_mealie`), collects Pydantic models, temporarily forces `extra="forbid"` on models that do not allow extras, runs `pydantic2ts` per package into `frontend/app/lib/api/types/<package>.ts` (underscores become hyphens), post-processes the output, and runs `pnpm lint --fix` on it. It also regenerates `components.d.ts` listing the global and layout Vue components. The result is the typing the frontend API clients rely on (see [[frontend]]); the files must never be edited manually.

### Test route helpers

`gen_py_pytest_routes.py` imports the real FastAPI app, forces every route into the schema, dumps OpenAPI and renders a Jinja template into `tests/utils/api_routes`, giving tests typed URL helpers (see [[testing]]). Because it is derived from the live routes, adding or renaming an endpoint requires regenerating.

## When to run it

Run `task dev:generate` after changing Pydantic schemas, adding routes, or adding locales or test data paths; PR review checks that generated files match the source. Locale handling has an extra rule: only `en-US` is edited by hand, since the others come from Crowdin.
