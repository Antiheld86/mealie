---
type: architecture
title: Event Bus, Webhooks and Notifications
description: How domain events are dispatched through EventBusService to Apprise notifier and scheduled-webhook listeners, how the minutely webhook task works, and how transactional email is sent.
tags: [events, webhooks, apprise, notifications, email]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-3df35d70ea8c19a8fb107044
    resource: repo://mealie/services/email/email_senders.py
  - id: openwiki-source-0236bb957b28f9de6ef45a8b
    resource: repo://mealie/services/email/email_service.py
  - id: openwiki-source-c22378313f05ba17aa198823
    resource: repo://mealie/services/event_bus_service/event_bus_listeners.py
  - id: openwiki-source-d9a8c847bbae58f774eb9997
    resource: repo://mealie/services/event_bus_service/event_bus_service.py
  - id: openwiki-source-7946e6c76f63f14a2004813d
    resource: repo://mealie/services/event_bus_service/event_types.py
  - id: openwiki-source-9cba2278178dad21434109f9
    resource: repo://mealie/services/event_bus_service/publisher.py
  - id: openwiki-source-ab9ee1d5e1bcc035d7ff06f3
    resource: repo://mealie/services/scheduler/tasks/post_webhooks.py
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Event Bus, Webhooks and Notifications

## Event bus

`EventBusService` (`mealie/services/event_bus_service/event_bus_service.py`) is the single dispatch point for domain events. Controllers that extend `BaseCrudController` get one through `EventBusService.as_dependency` (FastAPI `BackgroundTasks`, DB session, translator) and call `publish_event` (see [[backend-layers]]). Scheduled tasks construct it directly without background tasks.

`dispatch(integration_id, group_id, household_id, event_type, document_data, message)`:

1. Builds an `Event` whose message comes from `EventBusMessage.from_type`, localized by the translator.
2. If `household_id` is `None`, it needs a session and fans out to every household in the group; otherwise it targets one household.
3. For each household it either queues `_publish_event` on `BackgroundTasks` (so the HTTP response is not blocked) or runs it inline when no background tasks object exists.

`_publish_event` creates an `AppriseEventListener` and a `WebhookEventListener` for the group/household and, if a listener reports subscribers for the event, publishes to them.

### Event types

`EventTypes` (`event_types.py`) enumerates events such as `recipe_created/updated/deleted`, `user_signup`, data migration/export/import, meal plan entries, shopping lists, cookbooks, tags, categories and labels. `test_message` and `webhook_task` are internal and cannot be subscribed to. Each subscribable event type corresponds to a column on the notifier options table, so adding one requires a database migration (see [[database-and-migrations]]). Finer-grained detail belongs in the event's `EventDocumentType`/document data, which is not tied to the database.

## Listeners and publishers

`EventListenerBase` pairs a listener (find subscribers) with a publisher (deliver). `ensure_session`/`ensure_repos` use the provided session if present, or open a `session_context()` so listeners work both inside a request and in scheduled tasks.

- **Apprise notifiers**: `AppriseEventListener.get_subscribers` loads enabled `group_event_notifier` rows for the household and keeps those whose options enable the event type. For custom URL schemes (`form`, `json`, `xml` and their secure variants) it appends event metadata as `:`-prefixed query parameters. `ApprisePublisher` tags each URL with the event ID so a notification is sent once, then calls `apprise.notify`.
- **Webhooks**: `WebhookEventListener` only reacts to `webhook_task` events carrying `EventWebhookData`. It selects enabled webhooks for the household whose stored time of day falls in the event's time window (handling windows that wrap midnight UTC). For meal plan documents it fills the body with meals in the date range, and only publishes if a body exists. `WebhookPublisher` posts the JSON-encoded event through `mealie.pkgs.safehttp` with a 15-second timeout and the configured `http_allow_list`/`http_disallow_list`, which guards against SSRF to disallowed hosts.

## Scheduled webhook delivery

`post_group_webhooks` (`mealie/services/scheduler/tasks/post_webhooks.py`) is registered as a minutely scheduler callback (see [[app-lifecycle]]). It keeps a module-level `last_ran` timestamp, uses `[last_ran, now]` as the window, enumerates all groups and households, and dispatches a `webhook_task` event with mealplan document data. Currently only meal plan webhooks are supported. The household webhook controller can trigger the same function for one household (`controller_webhooks.py`) and sends test deliveries in the background via `post_test_webhook`, which skips the bus and publishes straight to the given webhook. See [[meal-plans-and-shopping-lists]] for the data being posted.

## Email

`EmailService` (`mealie/services/email/email_service.py`) renders a Jinja HTML template (`templates/default.html`) from an `EmailTemplate` with localized strings, and provides `send_forgot_password`, `send_invitation` and `send_test_email`. `send_email` returns `False` without sending if `SMTP_ENABLE` is off. The default sender (`DefaultEmailSender`) requires `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `SMTP_HOST` and `SMTP_PORT`, supports TLS or SSL via `SMTP_AUTH_STRATEGY`, and uses optional username/password.
