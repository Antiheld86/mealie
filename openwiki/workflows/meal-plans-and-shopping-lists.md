---
type: workflow
title: Meal Plans and Shopping Lists
description: How household meal plan entries, rule-driven random meals, the tokenized public iCal feed and the shopping list service (recipe-to-list conversion, item merging, on-hand foods) work.
tags: [mealplan, shopping-list, ical, household, workflow]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-2440ced9c8d86c026021549f
    resource: repo://mealie/repos/repository_meals.py
  - id: openwiki-source-cc2623256c8d5cbd0a5651c5
    resource: repo://mealie/routes/households/controller_mealplan_ical.py
  - id: openwiki-source-58406d685302f37d6dcfb222
    resource: repo://mealie/routes/households/controller_mealplan.py
  - id: openwiki-source-0df31ed97bf6dcefc56e6fea
    resource: repo://mealie/schema/meal_plan/plan_rules.py
  - id: openwiki-source-c3c980b792094d43628b98ec
    resource: repo://mealie/services/household_services/mealplan_ical_service.py
  - id: openwiki-source-a57420529f514d0f3cce3d87
    resource: repo://mealie/services/household_services/shopping_lists.py
  - id: openwiki-source-7e4192b0c1cba84aa4823636
    resource: repo://mealie/services/scheduler/tasks/delete_old_checked_shopping_list_items.py
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Meal Plans and Shopping Lists

Both features are household-scoped: their repositories extend `HouseholdRepositoryGeneric`, so every query is filtered to the caller's group and household (see [[multi-tenancy]]). Routes live in `mealie/routes/households/`; business logic is in `mealie/services/household_services/`.

## Meal plan entries

`GroupMealplanController` (`controller_mealplan.py`, a `BaseCrudController`) provides CRUD for plan entries and publishes `mealplan_entry_created/updated/deleted` events with a translated message so notifiers fire (see [[events-and-notifications]]). `RepositoryMeals` adds:

- `update` that forces `user_id` back to the stored value, because a plan's household derives from its user and a client-supplied `user_id` could otherwise move the entry to another household;
- `get_today` and `get_meals_by_date_range`, both requiring a household ID and ignoring entries with an `end_date` (week-long entries are not planned for a specific day).

`get_today` feeds the daily `create_mealplan_timeline_events` scheduled task, which records "made this" timeline events for planned recipes; `get_meals_by_date_range` feeds the scheduled meal plan webhooks.

### Rules and random meals

`/households/mealplans/rules` manages `PlanRules`, each with a `day` (weekday or `unset` = every day), an `entry_type` (breakfast, lunch, dinner, side, snack, drink, dessert or `unset`) and a `query_filter_string` that is validated by building it with the query filter builder (see [[search-and-filtering]]).

`POST /households/mealplans/random` picks a recipe by:

1. choosing the rule day: `unset` for date-range entries, otherwise the weekday of the plan date;
2. fetching matching rules and combining their filter strings with `QueryFilterBuilder.combine_filters`;
3. querying recipes across all households of the group (`household_id=None`, via `by_user` so user-specific data applies) with `order_by="random"` and a seed;
4. returning 404 ("no recipes match your rules") if nothing matches, otherwise saving a plan entry.

## Public iCal feed

A household manager (`Perm.HOUSEHOLD_MANAGE`) can create or delete a secret `mealplan_ical_token` stored in household preferences (`controller_mealplan_ical.py`). The public route `GET <prefix>/{token}` needs no login: `MealPlanICalService.get_feed` looks up preferences by token with unscoped repositories, resolves the household and group, then reads only that household's entries from a bounded recent window (so past entries do not accumulate in every poll), filters by entry type and whether notes are included, and renders an `.ics` document with `text/calendar` and `Cache-Control: no-cache`. An unknown token yields 404. The token column is intentionally not filterable, so it cannot be probed through query filters.

## Shopping lists

`ShoppingListService` (`shopping_lists.py`) is the main logic layer; the controller (`controller_shopping_lists.py`) exposes list CRUD, bulk item endpoints, label settings and recipe endpoints, and publishes list/item events.

### Scope check

Because recipes are group-wide but lists are household-scoped, the service calls `_require_lists_in_scope` before writing, returning 404 for any list not visible to the caller's household. Recipes are read through a group-level repo (`household_id=None`), so any recipe in the group can be a source.

### Merging items

`can_merge` allows two items to combine only when neither is checked, they reference the same food, and their units match or are convertible (both have a `standard_unit` that `UnitConverter` can convert). For foodless items the notes must match. `merge_items` sums quantities (converting units when possible), joins differing notes with `" | "`, merges extras, and combines recipe references, adding scales for the same recipe. `bulk_create_items` first consolidates the incoming items, then merges them into existing list items, optionally auto-assigning labels from food or display name (fuzzy matching with a default threshold of 80).

### Adding a recipe to a list

`add_recipe_ingredients_to_list` verifies the lists and recipes, calls `get_shopping_list_items_from_recipe` for each recipe, then bulk-creates the items and updates list-level recipe references. Conversion rules:

- sub-recipes referenced by an ingredient are expanded recursively with scale multiplied by the ingredient's quantity;
- when ingredients come from the stored recipe (rather than a caller-supplied subset), foods marked as on hand for the list's household are skipped (`_is_on_hand`);
- quantities are multiplied by the requested scale, and each item records a recipe reference with quantity, scale and note;
- duplicate ingredients within one recipe are combined by adding quantity rather than scale.

`remove_recipe_ingredients_from_list` reverses this: it ignores checked items and on-hand foods, and decrements or deletes items according to their recipe references. The daily `delete_old_checked_list_items` task walks every group, household and list and keeps only the 100 most recently updated checked items per list (`MAX_CHECKED_ITEMS`), deleting the rest and publishing item events (see [[app-lifecycle]]).
