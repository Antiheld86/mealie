---
type: workflow
title: Recipe Search, Query Filters and Suggestions
description: How Mealie paginates and searches records, how the query filter string language is parsed into SQLAlchemy expressions against filterable columns, and how the recipe suggestion finder ranks recipes by missing foods and tools.
tags: [search, query-filter, pagination, recipes, suggestions]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-d93a0bd070db18cf68ed104f
    resource: repo://mealie/repos/_recipe_suggestions.py
  - id: openwiki-source-0cc6582ff007cbc68d57ad95
    resource: repo://mealie/repos/repository_generic.py
  - id: openwiki-source-115f79de3ec86f5a08097e0f
    resource: repo://mealie/schema/_mealie/mealie_model.py
  - id: openwiki-source-c175230a9f31be1174450e9f
    resource: repo://mealie/schema/response/query_search.py
  - id: openwiki-source-46a86f517f23c4fae2713bfb
    resource: repo://mealie/services/matching.py
  - id: openwiki-source-b8c7f44255fe49fe0e12fe0a
    resource: repo://mealie/services/query_filter/builder.py
  - id: openwiki-source-84d675aaa8e5e69ae3df16ac
    resource: repo://mealie/services/query_filter/keywords.py
  - id: openwiki-source-39a8805dce2b2951a5b2335d
    resource: repo://mealie/services/query_filter/operators.py
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Recipe Search, Query Filters and Suggestions

## Pagination and search in repositories

Almost every list endpoint ends up in `RepositoryGeneric.page_all` (see [[backend-layers]]). It starts from the scope filter (group/household, see [[multi-tenancy]]), then optionally applies an `extra_filter`, a text `search`, a `query_filter` string and ordering, counts matches, and returns `PaginationBase` with page, per-page, total and total pages.

Details in `add_pagination_to_query`:

- `query_filter` is parsed by `QueryFilterBuilder`; a `ValueError` becomes an HTTP 400 with the message;
- the count is taken from a `DISTINCT` subquery before pagination, and eager-load options are applied afterwards so they do not distort counting;
- `per_page == -1` means "all" and `page == -1` means "last page"; out-of-range pages are clamped;
- with no explicit order and no search, results default to `created_at`.

### Text search

`add_search_to_query` builds a `SearchFilter` (`mealie/schema/response/query_search.py`). It uses **fuzzy** search only on PostgreSQL and only when the search string has no quoted parts; otherwise it uses **tokenized** search. Pre-processing replaces punctuation (except quote characters) with spaces, keeps quoted strings together as literal terms, and optionally transliterates and lowercases when the schema sets `_normalize_search`. Each schema declares `_searchable_properties`; `MealieModel.filter_search_query` then either:

- fuzzy: sets `pg_trgm.word_similarity_threshold` (default 0.5) and filters with the trigram `%>` operator, ordering by `<->>` distance on the first searchable property (this is why startup creates the `pg_trgm` extension, see [[database-and-migrations]]); or
- tokenized: ORs `LIKE %term%` across properties and orders by whether the first property matches the full phrase.

Normalized text columns on the models (via `SqlAlchemyBase.normalize`) support accent- and punctuation-insensitive matches.

## Query filter language

Clients pass `queryFilter` strings such as `recipeCategory.id IN ["..."] AND createdAt > $NOW-30d`. `QueryFilterBuilder` (`mealie/services/query_filter/builder.py`) implements it:

1. **Parsing**: the string is split into components (attribute, operator, value, logical operator, parentheses, lists in `[a,b]`), and parenthesis balance is validated. Camel-case attribute names are decamelized.
2. **Operators**: relational operators `= <> > < >= <=` (`RelationalOperator`) and keywords `IS`, `IS NOT`, `IN`, `NOT IN`, `CONTAINS ALL`, `LIKE`, `NOT LIKE` (`RelationalKeyword`); logical `AND`/`OR`. `IN`, `NOT IN` and `CONTAINS ALL` require a list; `IS`/`IS NOT` accept only `NULL`; `LIKE` only works on string columns.
3. **Placeholders**: `$NOW` with optional arithmetic (`$NOW+30d`, `$NOW-5M`; units y, m, d, H, M, S) is resolved at build time. The original raw value is retained for JSON serialization (`QueryFilterJSON`) so stored rules keep their placeholders.
4. **Value validation** is typed against the target column: strings are lowercased and compared via `lower(column)`; GUID values must be valid UUIDs; date and datetime values are parsed with `dateutil`; booleans accept values starting with t/y or `1`.
5. **Attribute resolution** (`get_model_and_model_attr_from_attr_string`) walks dotted paths through relationships (and association proxies), for example `user.name` or `recipe.group.preferences`. The final column must carry `info["filterable"]` (set with `FilterableColumn`), otherwise `NonFilterableValueError` is raised, which keeps private columns such as secret tokens out of filters.
6. **SQL generation**: each condition touching a relationship is wrapped in an `EXISTS` via `.any()`/`.has()` rather than joined, so one parent row is never duplicated (which would break `LIMIT`/`OFFSET` and make two conditions on the same relationship contradict each other). Ordering by a related attribute uses a correlated `MIN`/`MAX` scalar subquery for the same reason. Repository `column_aliases` can substitute computed expressions, for example recipe `last_made`.

`QueryFilterBuilder.combine_filters` ANDs several filter strings, validating each one and raising 400 for invalid ones. Meal plan random selection uses it to combine rules (see [[meal-plans-and-shopping-lists]]), and `PlanRulesCreate` validates user-entered rules the same way.

## Recipe-specific search

`RepositoryRecipes` (`mealie/repos/repository_recipes.py`) extends the generic repo with recipe filters: categories, tags, tools, foods and households, each with a "require all" option, plus cookbook filters (the recipe list route resolves a cookbook by ID or slug and applies its saved filter), and a per-user `last_made` computed from the user's household. `last_made` queries are only valid for authenticated household queries (HTTP 400 otherwise). Organizers are resolved against the repository's `group_id`, so cross-group IDs cannot be attached. Recipes created via import (see [[recipe-import-and-scraping]]) are immediately searchable through these paths.

## Suggestions

`RecipeSuggestionMixin` (`mealie/repos/_recipe_suggestions.py`) is mixed into `RepositoryRecipes` and implements the "what can I cook" finder, `find_suggested_recipes(params, food_ids, tool_ids, extra_filter)`:

- the user's food and tool IDs are expanded with household "on hand" items (`households_to_ingredient_foods`, `households_to_tools`);
- the query is scoped by group/household, then filtered by tools and foods, then by the optional `query_filter` through the same builder (400 on invalid input);
- ordering is by number of missing tools, then missing foods, then the caller's `order_by` (default `created_at`), limited by `params.limit`;
- foods can be satisfied by substitutions: recipe-level ingredient substitutions are checked before a food's own substitutions, and a note-only substitution (no food ID) can never satisfy an ingredient;
- each result reports `missing_foods`, `substituted_foods` and `missing_tools` alongside a `RecipeSummary`.

Food and unit name matching elsewhere (parsers, shopping lists) uses `mealie/services/matching.find_match`, which tries an exact dictionary hit first and falls back to the best `rapidfuzz` ratio at or above a threshold.
