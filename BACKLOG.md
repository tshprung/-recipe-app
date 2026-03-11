# Backlog — Later

Plans, bugs, and improvements deferred to a later release.

---

## Later / Backlog

- **Starter recipes (e.g. 3)** — Give new users a few initial recipes so they don’t start empty. Option: 3 recipes from famous national cooks, depending on the country chosen. Variant: at registration, show a checkbox list of topics/cuisines and let the user pick; then choose 3 recipes (e.g. from famous cooks in that country) for those topics. Needs design and possibly AI/search to select recipes.

- **Keep user logged in** — Persist login so users don’t have to log in every time (e.g. longer-lived or refresh tokens, “remember me”, secure storage).

- **Login with Google / Facebook** — Social login (OAuth) as an option alongside email/password.

- **DB efficiency and cost** — Review how data is stored and queried so it’s efficient and cheap to retrieve (indexes, query patterns, caching, archiving old data if needed).

- **Read recipe aloud** — Button to read the recipe out loud for hands-free cooking (e.g. browser TTS or integrate a read-aloud API).

- **Registration: default location from GPS** — On signup, try to get location via GPS (or IP/browser) and prefill country/city as default so users don’t have to type it.

- **Ingredient alternatives — credits** — Surface and enforce that using ingredient alternatives consumes credits (e.g. 1 token per lookup). Show remaining credits in the alternatives flow and handle “insufficient credits” (e.g. message or upgrade prompt). Currently the feature ignores credit cost.

---

*Move items here when deferring; move back to active work when prioritising.*
