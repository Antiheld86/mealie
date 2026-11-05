---
type: architecture
title: App Startup, Settings and Scheduler
description: How the Mealie FastAPI app is assembled, what runs at startup, how settings are obtained, how the in-process scheduler runs periodic tasks, and how production serves the Nuxt SPA.
tags: [fastapi, lifespan, scheduler, settings, spa]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-3cf93211abde5de6c3170d3d
    resource: repo://mealie/app.py
  - id: openwiki-source-000e443e7518a4aeb09f59e2
    resource: repo://mealie/core/config.py
  - id: openwiki-source-33c7620a908409ebeadc85b1
    resource: repo://mealie/routes/spa/__init__.py
  - id: openwiki-source-cb7892c4722492be0e27a450
    resource: repo://mealie/services/scheduler/scheduler_registry.py
  - id: openwiki-source-ec16b7c2b54e0560f29ef209
    resource: repo://mealie/services/scheduler/scheduler_service.py
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# App Startup, Settings and Scheduler

## Entrypoints

`mealie/app.py` builds the module-level `app = FastAPI(...)` and also defines a `main()` that runs uvicorn with `reload=True` for development. `mealie/main.py` is the production launcher: it imports `settings` from `mealie.app` and creates its own wildcard listener socket (dual-stack IPv6, falling back to IPv4 `0.0.0.0`).

## Lifespan

The app registers `lifespan_fn` as its lifespan. On startup it:

1. imports `mealie.db.init_db` and calls `init_db.main()` (database initialization, see [[database-and-migrations]]),
2. calls `start_scheduler()`,
3. logs the settings (excluding `SECRET`, `SESSION_SECRET`, `DB_URL`, `DB_PROVIDER`) and which SMTP/LDAP/OIDC features are enabled,
4. warns if `BRANDING_LOGO_PATH` is not a readable image file.

Shutdown only logs.

## Middleware

`GZipMiddleware` (min size 1000), `SessionMiddleware` (keyed by `SESSION_SECRET`) and `LocaleContextMiddleware` are always added. CORS for `http://localhost:3000` is added only when `settings.PRODUCTION` is false, which is how the separate Nuxt dev server (port 3000) can call the backend (port 9000).

`LocaleContextMiddleware` reads `Accept-Language`, builds a translator and locale config, and stores them in context vars so any code inside the request can call `get_locale_context`.

## Settings

`get_app_settings()` in `mealie/core/config.py` is `lru_cache`d, so it is a process-wide singleton built by `app_settings_constructor` from the env file, production flag and data directory. Code should call it rather than instantiate `AppSettings` directly.

## Scheduler

`SchedulerRegistry` holds three class-level lists of callbacks (daily, hourly, minutely). `start_scheduler()` in `app.py` registers:

- daily: purge expired tokens, group registration tokens, password reset tokens, group data exports; create mealplan timeline events; delete old checked shopping-list items
- minutely: `post_group_webhooks`
- hourly: `locked_user_reset`

`SchedulerService.start()` launches the minutely and hourly loops via the `repeat_every` decorator (`mealie/services/scheduler/runner.py`), and spawns `schedule_daily()` as an asyncio task that sleeps until `DAILY_SCHEDULE_TIME_UTC` (rolling to the next day if already past) before running the daily loop. The "minutely" loop actually fires every 5 minutes. Each callback runs through `_scheduled_task_wrapper`, which logs and swallows exceptions so one failing task does not stop the others.

Task implementations live in `mealie/services/scheduler/tasks/`. Webhook delivery is covered in [[events-and-notifications]].

## Routers and SPA serving

`api_routers()` includes the main `router`, `media_router` and utility routes. Only when `PRODUCTION` is true and `TESTING` is false does it call `spa.mount_spa(app)`, so tests and development never serve the static frontend.

`mount_spa` (in `mealie/routes/spa/__init__.py`) returns silently if the `STATIC_FILES` directory is missing. Otherwise it reads `index.html`, registers server-side meta-tag routes for recipe pages and shared recipes (`/g/{group_slug}/r/{recipe_slug}`, `/g/{group_slug}/shared/r/{token_id}`), a web manifest route, and mounts `SPAStaticFiles` at `/`. `SPAStaticFiles` falls back to `index.html` on 404, rewrites HTML 404s to 200, turns directory redirects into relative paths (avoiding Host-header-derived redirects), caches `_nuxt/*` immutably and marks HTML `no-cache`. Meta tag values are HTML-escaped to prevent XSS.

After routers are included, a loop de-duplicates route tags that `@controller` would otherwise duplicate in the OpenAPI spec.
