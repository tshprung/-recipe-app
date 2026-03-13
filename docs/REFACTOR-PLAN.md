# Refactor plan: smaller, tighter, more efficient

This plan is based on a pass over the codebase. Items are ordered by impact and ease; do in phases.

---

## Phase 1: Shared constants (high impact, low risk)

**Goal:** One source of truth for dish types, diets, allergens, countries, languages, and storage keys. Reduces drift and duplication across 5+ files.

| What | Where it’s duplicated | Action |
|------|------------------------|--------|
| **DISH_TYPES** | `DiscoverPage.jsx`, `OnboardingPage.jsx` | Add `frontend/src/constants/recipes.js` (or `dishTypes.js`) and import in both. |
| **DIET_OPTIONS** | `DiscoverPage.jsx`, `OnboardingPage.jsx`, `WhatCanIMakePage.jsx` (Onboarding uses `label`, others `labelKey`) | Single list with `key` + `labelKey`; all pages use `t(labelKey)`. |
| **ALLERGENS** | `OnboardingPage.jsx`, `SettingsPage.jsx` | Add `frontend/src/constants/allergens.js`; both import. Keep in sync with backend `ALLOWED_ALLERGEN_CODES` (doc or shared source). |
| **COUNTRIES** | `OnboardingPage.jsx`, `SettingsPage.jsx` | Add `frontend/src/constants/countries.js` (or in a single `constants/index.js`). |
| **TARGET_LANGUAGES** | `OnboardingPage.jsx`, `SettingsPage.jsx` (Settings has more entries) | One list (e.g. Settings’ version) in `constants/languages.js`; both import. |
| **Storage keys** | `LanguageContext.jsx`, `client.js`, `AuthContext.jsx`, `SettingsPage.jsx` (`recipe-app-lang`, `recipe_app_remember_me`, `trial_token`) | Add `frontend/src/constants/storageKeys.js`; client, AuthContext, LanguageContext, Settings import. |
| **Variant/diet labels** | `RecipeDetailPage.jsx` (VARIANT_OPTIONS, VARIANT_BADGE, variantLabelKey) vs DIET_OPTIONS elsewhere | Use shared diet/variant constant (keys + labelKeys) for detail tabs, Discover, Onboarding, WhatCanIMake. |

**Deliverable:** New `frontend/src/constants/` module and removal of duplicated literals from the listed files.

---

## Phase 2: Backend helpers (less duplication, consistent behavior)

**Goal:** Reuse “user/trial recipes”, “get recipe or 404”, and allergen validation instead of repeating the same blocks.

| What | Current pattern | Action |
|------|------------------|--------|
| **Recipes for user or trial** | In `recipes.py`: list_recipes, list_collections, what_can_i_make each do “if user: filter by user_id else filter by trial_session_id”. | Add `_recipes_for_user_or_trial(db, current_user, trial_session)` (returns query or list); use in all three. |
| **Get recipe or 404** | Many endpoints: `recipe = db.get(...); if not recipe or not _recipe_owned_by(...): raise 404`. | Add `get_recipe_or_404(recipe_id, current_user, trial_session, db) -> Recipe`; use in get_recipe, update_notes, meta, collections, adapt, ingredient-match, image, replace-ingredient, etc. |
| **Allergen validation** | `schemas.py`: similar logic in `UserRegister`, `UserSettings`, `UserSettingsUpdate` validators. | Add `validate_allergen_codes(v: list[str] | None) -> list[str]` and call from all three. |
| **Claim-starter / profile apply** | `users.py`: long if-block applying many fields from payload. | Loop over `payload.model_dump(exclude_unset=True)` with an allowlist and `setattr(current_user, k, v)`. |
| **Shopping list categorized items** | `shopping_lists.py`: get_shopping_list and email_shopping_list both do _get_recipe_ids → _collect_ingredients → categorize_ingredients (same try/except). | Add `_get_categorized_items(recipe_ids, user_id, db, user)` returning (recipe_ids, items) or raising; use in both. |

**Deliverable:** Helpers in `backend/app/routers/recipes.py` (or `recipes_helpers.py`) and `backend/app/schemas.py` / `routers/shopping_lists.py`; endpoints refactored to use them.

---

## Phase 3: RecipeDetailPage and LanguageContext (smaller, clearer)

**Goal:** Shrink large files and separate concerns.

### RecipeDetailPage.jsx (~1337 lines)

1. **Constants and pure helpers**  
   Move to `frontend/src/pages/RecipeDetail/constants.js` and `utils.js` (or similar):  
   TAG_COLORS, NOTE_META, VARIANT_OPTIONS, VARIANT_BADGE, CONTENT_KEYWORDS;  
   `parseAmountLeading`, `scaleIngredientLine`, `variantLabelKey`, `variantDisplayLabel`, `detectContentTags`.

2. **Hooks**  
   Extract at least:  
   - `useRecipeDetail(id)` – load recipe + variants, loading/error.  
   - `useServings(recipe, user)` – displayServings, baseServings, getBaseServings, handleSaveServingsAsDefault.  
   - `useAdaptation(recipeId)` – variants, activeTab, adapt loading/error, handleAdapt, dropdown state.  
   - `useIngredientMatch(recipeId)` – myIngredientsText, matchResult, matchLoading, handleCheckIngredients.  
   - `useCollections(recipeId)` – newCollectionInput, collectionsSaving, handleUpdateCollections, handleAddCollection, handleRemoveCollection.

3. **Subcomponents**  
   Under `frontend/src/components/RecipeDetail/`:  
   RecipeHero, IngredientList, StepsList, VariantTabs, AdaptDropdown, AlternativesModal, CollectionsPills, MatchResultBlock (and any other clear blocks).  
   RecipeDetailPage then composes these and uses the hooks.

### LanguageContext.jsx (~718 lines)

- Move the large `translations` object into `frontend/src/locales/en.js`, `he.js`, `pl.js` (or JSON), and import in the context.
- Keeps the context thin (state + `t()` + provider) and makes translations easier to edit and review.

**Deliverable:** Smaller RecipeDetailPage, new hooks and components, and locale files for LanguageContext.

---

## Phase 4: Split recipes router (backend)

**Goal:** `backend/app/routers/recipes.py` (~1160 lines) split by domain so each file is easier to work on.

| New module | Contents |
|------------|----------|
| **recipes_crud.py** | create, list, get, delete, from-ai-suggestion; shared `get_recipe_or_404` and `_recipes_for_user_or_trial` (or in helpers). |
| **recipes_adapt.py** | adapt, variants, replace-ingredient, ingredient-alternatives; adaptation-specific helpers. |
| **recipes_discover.py** | what-can-i-make, discover. |
| **recipes_meta.py** | notes, meta, collections, image upload/delete, ingredient-match. |
| **recipes_helpers.py** | _recipe_owned_by, _recipe_ingredient_lines, _user_ingredients_set, _ingredient_matches_user, _normalize_ingredient_line, _COMMON_PANTRY, _recipe_matches_query, _normalize_adapt_types, etc. |

Main `recipes.py` can re-export routers or mount them under the same prefix so URL paths stay the same.

**Deliverable:** Several smaller router modules + shared helpers; same API surface.

---

## Phase 5: Error handling and user deletion (consistency)

**Goal:** One pattern for API errors and one place for “delete user and data”.

### Frontend

- Add `getErrorMessage(err, t, fallbackKey = 'somethingWentWrong')` (e.g. in `frontend/src/utils/errors.js` or inside a small api helper). Use it everywhere we currently do `setError(e.message || t('...'))` or similar so fallbacks and i18n are consistent.
- Optionally: a small ErrorBanner component used on major pages so UI and copy are consistent.

### Backend

- Add small helpers, e.g. `raise_503(e)` / `raise_502(e, context="...")`, and use them where we raise 502/503 so status and wording are consistent.
- Add `services/user_deletion.py` with `delete_user_and_data(user_id, db)` (recipes, shopping list, cache, substitutions, etc.). Call it from `users.py` (delete account) and `admin.py` (delete user) so behavior and future relations stay in sync.

**Deliverable:** Shared error helpers (frontend + backend), single user-deletion service, and endpoints refactored to use them.

---

## Phase 6: Optional cleanups

- **MAX_TRIAL_ACTIONS:** Defined in frontend (AuthContext) and backend (quota.py). Consider one source (e.g. env or API) if you want to change it in one place.
- **API client `t()`:** `client.js` has a minimal `t()` for pre-React network errors. Either move those strings into LanguageContext and resolve them the same way, or document that client has a minimal fallback and keep “real” i18n in context.
- **Pagination:** list_recipes and list_collections currently load all rows; add DB-level filtering and optional pagination when recipe counts grow.
- **RecipeDetailPage:** Further split of remaining state (e.g. rating, notes, image upload) into small hooks or components as needed.

---

## Suggested order

1. Phase 1 (constants) – quick wins, no behavior change.
2. Phase 2 (backend helpers) – reduces duplication and keeps 404/allergen behavior consistent.
3. Phase 3 (RecipeDetailPage + LanguageContext) – biggest readability and maintainability gain.
4. Phase 4 (split recipes router) – easier navigation and smaller diffs.
5. Phase 5 (errors + user deletion) – consistency and single place for dangerous operations.
6. Phase 6 as needed.

---

*Generated from a codebase review. Adjust scope and order to match your priorities and capacity.*
