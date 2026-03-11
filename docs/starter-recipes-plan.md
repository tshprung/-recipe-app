# Starter recipes for new users — plan (with author attribution)

## Goal

New users get **3 initial recipes** based on **target country**, each from a **famous cook** in that country (TV show winner, own show, cookbook author). The app must **emphasize the author**: **name**, **short description**, and optionally a **representative image**.

## User-facing rules (from feedback)

- User sees the 3 recipes **even if not verified** (show in list regardless of `is_verified`).
- Recipes are **added once**, on **first login** after registration; if the user deletes them and logs in again, they **do not** come back (one-time gift).
- Starter recipes are **free** and **do not use credits** (no quota increment).
- **Backlog (next step):** Cache the 3 recipes per country in a shared DB table so the next user from the same country gets them from the DB without AI.

## Author attribution (famous cook per recipe)

Each starter recipe should clearly show who the author is:

- **Author name**
- **Short description** (e.g. "Host of X", "Winner of Y", "Author of Z cookbook")
- **Optional representative image** (photo or logo)

**Backend:**

- Add optional fields to **Recipe**: `author_name`, `author_bio` (short, 1–2 sentences), `author_image_url` (nullable). Migration: new columns on `recipes` table.
- **AI prompt** in `get_starter_recipes`: ask for **per-recipe** `author_name`, `author_bio` (why they are famous in that country: TV show, books, restaurant). Optionally `author_image_url` (or use a placeholder/static image per country).
- **Schemas:** Extend `RecipeOut` with optional `author_name`, `author_bio`, `author_image_url`.

**Frontend:**

- Recipe **card** (list) and **recipe detail**: when `author_name` or `author_bio` is present, show "By [Name]", short bio, and if present a small **representative image**. Make the famous-cook attribution visible and appealing.

When we add the "cache per country" feature, the cached template will also store author info.

## Implementation summary

1. **Trigger:** On **first login** (in `POST /api/auth/login`): after successful auth, if user has **0 recipes** and **not** `starter_recipes_added`, call logic to create 3 recipes and set `starter_recipes_added = True`. Do **not** run when `starter_recipes_added` is already true (so deleted recipes are not re-added).
2. **Recipe model:** Add `starter_recipes_added: bool` on User; add optional `author_name`, `author_bio`, `author_image_url` on Recipe.
3. **AI service:** `get_starter_recipes(country, language)` returns 3 items: each `{ title, ingredients, steps, author_name, author_bio, author_image_url? }`. Prompt: famous cook from that country, with name and short bio (TV show, books, etc.).
4. **No credits:** When creating these 3 recipes, do not increment `transformations_used`.
5. **Visibility:** Recipe list is available and shows these 3 recipes even for unverified users (no gate on "verified" for listing).
6. **Backlog:** "Starter recipes cache per country" — store generated 3 recipes (with author info) per country in shared table; later users from same country get from DB, no AI.
