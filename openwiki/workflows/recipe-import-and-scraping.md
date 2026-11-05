---
type: workflow
title: Recipe Creation, Scraping and AI Import
description: How recipes enter Mealie from URLs, raw HTML/JSON, bulk URL lists, zip files and AI sources, covering the scraper strategy chain, cleaning, image download, the AI import workflow and ingredient parsers.
tags: [recipes, scraper, openai, import, ingredient-parser]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-04T19:23:01.839Z
sources:
  - id: openwiki-source-f31f8af68b8efb1e69c44d94
    resource: repo://mealie/schema/recipe/recipe_ingredient.py
  - id: openwiki-source-e717c8d803d3a1bce356f794
    resource: repo://mealie/services/openai/openai.py
  - id: openwiki-source-d4ef95385c46fb381ecdecfa
    resource: repo://mealie/services/parser_services/ingredient_parser.py
  - id: openwiki-source-2523c9f6bc966502c56642ac
    resource: repo://mealie/services/recipe/ai_recipe_service.py
  - id: openwiki-source-e05960a7f1be96db3d272935
    resource: repo://mealie/services/recipe/import_workflow/workflow.py
  - id: openwiki-source-236b8ceef0ff680a147f2d39
    resource: repo://mealie/services/recipe/recipe_data_service.py
  - id: openwiki-source-f2830c93e1bba5baf34c9be4
    resource: repo://mealie/services/recipe/recipe_service.py
  - id: openwiki-source-f190e115f8f0592bc317a041
    resource: repo://mealie/services/scraper/recipe_bulk_scraper.py
  - id: openwiki-source-4091e7e0fb8e5ea7089909a5
    resource: repo://mealie/services/scraper/recipe_scraper.py
  - id: openwiki-source-d321b144da5b77ec93e3bef5
    resource: repo://mealie/services/scraper/scraper_strategies.py
  - id: openwiki-source-06f73fe4ed33feb997734451
    resource: repo://mealie/services/scraper/scraper.py
generated: { by: "claude-code", at: "2026-11-04T19:23:01.839Z" }
---

# Recipe Creation, Scraping and AI Import

Routes are in `mealie/routes/recipe/recipe_crud_routes.py`; logic lives in `mealie/services/scraper/`, `mealie/services/recipe/` and `mealie/services/openai/`. The controllers delegate to services as described in [[backend-layers]].

## Entry points

| Route | Purpose |
| --- | --- |
| `POST /recipes/create/url` and `/create/url/stream` | Scrape a URL and save it |
| `POST /recipes/create/html-or-json` (+ `/stream`) | Parse supplied HTML or a schema.org JSON recipe like a URL; a full Mealie export JSON is imported with its full structure |
| `POST /recipes/create/ai` (+ `/stream`) | Build a recipe from text, images and/or URL using the AI workflow |
| `POST /recipes/create/url/bulk` | Queue many URLs (returns 202) |
| `POST /recipes/create/zip` | Import a recipe zip (Mealie export) |
| `POST /recipes` | Create an empty/named recipe |
| `POST /recipes/test-scrape-url` | Check whether scraping a URL works |

The `/stream` variants send progress as server-sent events (`SSEDataEventMessage`, `SSEDataEventDone` carrying the new slug, or an error event); the non-stream variants consume the same generator and return the slug or raise HTTP 400/500. Failures are mapped to translated, user-safe messages (rate limit, AI not enabled, video download failed, generic AI failure) rather than exposing exception text.

## URL scraping

`create_from_html` (`scraper/scraper.py`) extracts the first `http(s)://`/`www.` URL from the input (400 `BAD_RECIPE_DATA` if none), then asks `RecipeScraper.scrape` for a recipe. `RecipeScraper` fetches the page with `safehttp.resilient_fetch` unless HTML was supplied, then tries strategies in order, which matters:

1. `RecipeScraperPackage`: structured-data scraping (the `recipe_scrapers` package and schema.org data);
2. `RecipeScraperOpenAITranscription`: only if the group enabled an audio provider and the URL is a video URL; transcribes it;
3. `RecipeScraperOpenAI`: only if the group's AI is enabled; runs the AI import workflow on the page;
4. `RecipeScraperOpenGraph`: a last-resort fallback from Open Graph metadata.

Each strategy checks `can_scrape()`; an exception or empty result moves on to the next. The first result is passed through `cleaner.clean` (normalizing times, ingredients, instructions, images, etc.); if cleaning fails the next strategy is tried. `safehttp` guards against slow or oversized responses and SSRF to disallowed hosts, and cycles through TLS browser impersonations to get past bot detection.

### Finalizing

`finalize_scraped_recipe` assigns a UUID, downloads the image, and guarantees a name and slug. `RecipeDataService.scrape_image` accepts a string, list (choosing the largest by `Content-Length` using concurrent HEAD requests) or dict URL, fetches via `fetch_image` (requires an `image/*` content type), and writes through the minifier, which converts to webp. The recipe's `image` is set to a fresh cache key only if a file was actually written, so the frontend never requests an image that does not exist. The recipe is not persisted by the scraper; the caller saves it.

### Persisting

`RecipeService.create_one` (`recipe/recipe_service.py`) builds the recipe with defaults, applies the household's default recipe settings (public, show nutrition, show assets, landscape, comments) when none were given, saves it via the scoped repository (see [[multi-tenancy]]), converts any incoming rating into a user rating, and creates the first timeline event. `clean_recipe_dict` and the `_transform_*` helpers sanitize imported data so foods, units, tools, categories and sub-recipes are re-resolved within the importing group instead of trusting foreign IDs.

### Bulk import

`RecipeBulkScraperService.scrape` creates a "Bulk Import" report, scrapes URLs concurrently with a semaphore of 3, applies per-URL tags/categories, saves each recipe and records a per-URL report entry. Overall report status is success, failure or partial depending on entries, the same convention used by third-party migrations (see [[backups-and-migrations-import]]).

## AI import workflow

`AIRecipeService.create_from_ai` stores uploaded images in a temp directory and calls `build_recipe`, which rejects empty input, checks that the group's AI provider settings enable AI (and an image provider when images are supplied), and runs `RecipeImportWorkflow` (`recipe/import_workflow/workflow.py`). The workflow runs ordered steps, skipping those whose `should_run` is false; a failing required step aborts, a failing optional step is logged and skipped:

1. `CompileSourceStep` compiles every source (web page, structured data, images, transcription) into one labelled source document, preferring user-supplied content when sources disagree;
2. `BuildRecipeStep` turns it into a draft recipe;
3. `TranslateRecipeStep` optionally translates;
4. `ResolveOrganizersStep` maps categories/tags (optionally creating new ones).

The workflow never persists. It is used by `/recipes/create/ai` and by `RecipeScraperOpenAI`, so ordinary well-marked-up sites never invoke it. The first uploaded image becomes the cover image.

`OpenAIService` (`services/openai/openai.py`) loads the group's provider settings and the default, audio and image providers from the repositories, so API keys and models are per group and configured through group AI provider routes, not global settings.

## Ingredient parsing

`get_parser` (`parser_services/ingredient_parser.py`) selects an `ABCIngredientParser` from `RegisteredParser`: `nlp` (default, `NLPParser`), `brute` (`BruteForceParser`) or `openai` (imported lazily). Parsers convert ingredient strings to `ParsedIngredient`, then `find_ingredient_match` uses `DataMatcher` to match foods and units by name or alias with fuzzy thresholds. `DataMatcher` is also used by the shopping list service (see [[meal-plans-and-shopping-lists]]). Recipes created here are then searchable as described in [[search-and-filtering]].
