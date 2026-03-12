# Backlog — Later

Plans, bugs, and improvements deferred to a later release.

---

## Later / Backlog

- **Starter recipes (e.g. 3)** — Give new users a few initial recipes so they don’t start empty. Option: 3 recipes from famous national cooks, depending on the country chosen. Variant: at registration, show a checkbox list of topics/cuisines and let the user pick; then choose 3 recipes (e.g. from famous cooks in that country) for those topics. Needs design and possibly AI/search to select recipes.

- ~~**Keep user logged in**~~ — Done: “Keep me logged in” checkbox; token in localStorage vs sessionStorage.

- ~~**Login with Google / Facebook**~~ — Done: OAuth routes and “Continue with Google” / “Continue with Facebook” on login (set GOOGLE_CLIENT_ID/SECRET, FACEBOOK_APP_ID/SECRET, FRONTEND_URL, OAUTH_REDIRECT_BASE). Google live; Facebook code in place, pending Facebook app onboarding/approval.

- **DB efficiency and cost** — Review how data is stored and queried so it’s efficient and cheap to retrieve (indexes, query patterns, caching, archiving old data if needed).

- **Read recipe aloud** — Button to read the recipe out loud for hands-free cooking (e.g. browser TTS or integrate a read-aloud API).

- ~~**Registration: default location from GPS**~~ — Done: “Use my location” on register uses IP geolocation (GET /api/meta/geo) to prefill country/city/zip.

- **Starter recipes cache per country** — Store the 3 AI-generated starter recipes (with author name, bio, image) per country in a shared DB table so the next user from the same country gets them from the DB without calling OpenAI (saves cost and latency).

- **Post-registration location/language step (OAuth)** — When registering via Google (or other OAuth), after first login show the location and language selection screen before going to the main recipes page. Currently OAuth users go straight to their recipe list.

- **Dish-type preferences at registration** — After the language/location step, add a page where the user selects types of dishes they like (e.g. pasta, pizza, beef, chicken, soups, salads, baking, breakfast). Store and use for suggestions/starter recipes.

- **Allergens page** — A page (or section) where the user can declare allergens they are sensitive to or do not want in their diet. Use when suggesting or adapting recipes so results exclude or flag those ingredients.

- **Settings: centralise preferences** — All of the above (location, languages, dish-type preferences, allergens) should be editable from the Settings page, not only at registration.

- **Discover / find recipes from internet or AI** — A page or tab where the user can choose recipe type, diet, restrictions (and optionally a specific or famous cook) and get suggestions from the web or AI. Parameters to consider: dish type, diet, allergens, cuisine, cook name, max time, ingredients to include/avoid. Ideas: search by famous cook; exclude specific ingredients; "what's in season"; limit to one source (e.g. trusted sites). Decide what NOT to allow (e.g. unsafe sources, unclear licensing).

- **Serving size / number of people** — In settings and/or when opening a recipe, let the user set how many people they are cooking for. Scale recipe quantities accordingly and show "Serves N" in the recipe.

- **Ingredient alternatives — credits** — Surface and enforce that using ingredient alternatives consumes credits (e.g. 1 token per lookup). Show remaining credits in the alternatives flow and handle “insufficient credits” (e.g. message or upgrade prompt). Currently the feature ignores credit cost.

---

*Move items here when deferring; move back to active work when prioritising.*
