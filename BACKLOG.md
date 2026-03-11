# Backlog — Later

Plans, bugs, and improvements deferred to a later release.

---

## Later / Backlog

- **Starter recipes (e.g. 3)** — Give new users a few initial recipes so they don’t start empty. Option: 3 recipes from famous national cooks, depending on the country chosen. Variant: at registration, show a checkbox list of topics/cuisines and let the user pick; then choose 3 recipes (e.g. from famous cooks in that country) for those topics. Needs design and possibly AI/search to select recipes.

- ~~**Keep user logged in**~~ — Done: “Keep me logged in” checkbox; token in localStorage vs sessionStorage.

- ~~**Login with Google / Facebook**~~ — Done: OAuth routes and “Continue with Google” / “Continue with Facebook” on login (set GOOGLE_CLIENT_ID/SECRET, FACEBOOK_APP_ID/SECRET, FRONTEND_URL, OAUTH_REDIRECT_BASE).

- **DB efficiency and cost** — Review how data is stored and queried so it’s efficient and cheap to retrieve (indexes, query patterns, caching, archiving old data if needed).

- **Read recipe aloud** — Button to read the recipe out loud for hands-free cooking (e.g. browser TTS or integrate a read-aloud API).

- ~~**Registration: default location from GPS**~~ — Done: “Use my location” on register uses IP geolocation (GET /api/meta/geo) to prefill country/city/zip.

- **Starter recipes cache per country** — Store the 3 AI-generated starter recipes (with author name, bio, image) per country in a shared DB table so the next user from the same country gets them from the DB without calling OpenAI (saves cost and latency).

- **Ingredient alternatives — credits** — Surface and enforce that using ingredient alternatives consumes credits (e.g. 1 token per lookup). Show remaining credits in the alternatives flow and handle “insufficient credits” (e.g. message or upgrade prompt). Currently the feature ignores credit cost.

---

*Move items here when deferring; move back to active work when prioritising.*
