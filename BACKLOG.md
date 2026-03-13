# Backlog — Later

Plans, bugs, and improvements deferred to a later release.

---

## Focus areas (recently completed)

- **Serving size scaling + per-recipe override** — Implemented: servings control (minus/plus) on recipe detail, client-side ingredient scaling, and “Save as default for this recipe” via `PATCH /recipes/{id}/meta` (`servings_override`).

- **“What I have” vs “what I need”** — Implemented: “Ingredients I have” textarea on recipe detail, “Check” calls `POST /recipes/{id}/ingredient-match`, shows “You have X of Y ingredients” and “Add recipe to shopping list”.

- **Discover new recipes** — Implemented: Discover page with dish types, diet filters, max time; `POST /recipes/discover` returns 1–2 AI-suggested recipes; “Save to my recipes” for logged-in users.

- **Recipe organization (collections)** — Implemented: `collections` on recipe (list of strings), `PATCH /recipes/{id}/collections`, `GET /recipes/collections`; recipe detail pills to add/remove collections; recipe list filter by collection.

---

## Later / Backlog

- **Starter recipes (e.g. 3)** — New users already get 3 starter recipes (often from famous national cooks) based on their onboarding settings (country, languages, dish-type preferences, diet). Remaining work: improve how we pick and explain these recipes (“why these?”), and decide what to do for users who register directly on `/login` without going through onboarding.

- **DB efficiency and cost** — Review how data is stored and queried so it’s efficient and cheap to retrieve (indexes, query patterns, caching, archiving old data if needed).

- **Read recipe aloud** — Button to read the recipe out loud for hands-free cooking (e.g. browser TTS or integrate a read-aloud API).

- **Starter recipes cache per country** — Store the 3 AI-generated starter recipes (with author name, bio, image) per country in a shared DB table so the next user from the same country gets them from the DB without calling OpenAI (saves cost and latency).

- **Post-registration location/language step (OAuth)** — When registering via Google (or other OAuth), after first login show the location and language selection screen before going to the main recipes page. Currently OAuth users go straight to their recipe list.

- **Dish-type preferences at registration** — After the language/location step, add a page where the user selects types of dishes they like (e.g. pasta, pizza, beef, chicken, soups, salads, baking, breakfast). Store and use for suggestions/starter recipes.

- **Adapt recipe for kids** — Let the user take any recipe and get a kid-friendly version: safe (no choking hazards, no honey under 1, food-safe) and healthier (less salt/sugar, age-appropriate portions and textures). Optional: store "cooking for kids" and age range(s) (e.g. 1 and 4) in settings; use in adaptation and in "find recipe" filters.

- **Recipe notes: high sugar / high salt / spicy etc.** — Allow notes or tags on each recipe (or per variant) such as high sugar, high salt, spicy, so users can see at a glance and filter. Could be AI-derived on import or user-set.

- **Household profiles / per-recipe serving override** — Optional profiles (e.g. different allergens per person) or at least override "cooking for N" per recipe when different from default. (Per-recipe override is done; household profiles are future.)

- **Meal plan (week view)** — Plan which recipes to cook on which days; feed into shopping and reduce "what's for dinner" decisions.

- **"Would make again" toggle + surfaces** — Add quick toggle and filter/list views (e.g. Favorites-like, or “Top rated / would make again”).

- **Leftovers note** — Optional note or tag that a recipe keeps well or how to reheat, for next-day planning.

- **Difficulty or "beginner-friendly"** — Tag or filter recipes by difficulty or time (e.g. under 30 min) so they can pick by busy vs relaxed days.

- **Update existing recipe after changing location/language** — Backend already exposes `/recipes/{id}/relocalize` to re-run translation for the user’s current settings. Remaining work: add a clear “Re-localize to my current settings” action on the recipe detail page and align the copy with what Settings promises. (Deprioritised: changing location is rare.)

---

*Move items here when deferring; move back to active work when prioritising.*
