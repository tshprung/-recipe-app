# Recipe App Backlog

Backlog ordered by priority (1 = highest). Each section: Goal, UX flow, Backend, Frontend, Edge cases, MVP.

---

## 1. Weekly Meal Planner

**Goal**

Generate a 5–7 day meal plan personalized to user preferences and auto-create a shopping list.

**UX flow**

- New page: `/meal-plan`
- Button: "Generate weekly plan"
- User selects: number of days, diet filters, budget (optional)
- Output: list of days with recipes, ability to replace a meal, "Add all to shopping list"

**Backend**

- Add table: `meal_plans`
  - `id`
  - `user_id`
  - `start_date`
  - `data` (JSON)

**AI prompt**

```
Generate a weekly meal plan.

Constraints:
- Diet: {diet}
- Allergens: {allergens}
- Household: {household}
- Max time per meal: {time}
- Budget: {budget if exists}

Output:
- 5–7 meals
- Each meal: name, short description, estimated time
```

**Frontend**

- Card per day
- Replace button → regenerate single meal

**Edge cases**

- No recipes → fallback to Discover
- Too restrictive filters

**MVP**

- No drag & drop
- No calendar integration

---

## 2. Cook Mode

**Goal**

Turn recipe into step-by-step cooking assistant.

**UX flow**

- Button: "Start cooking"
- Fullscreen mode: step text (large), "Next" / "Back", timer button per step

**Backend**

- No major changes (reuse recipe steps)

**Frontend**

- New component: `CookMode.jsx`
- State: `currentStep`, `activeTimers`

**AI enhancement (optional)**

- Split steps: break recipe into very clear, short cooking steps for real-time cooking. Each step must be simple and actionable.

**Edge cases**

- Long paragraphs → must split
- Missing timing info

**MVP**

- No voice yet
- Basic timer only

---

## 4. Cost Optimization

**Goal**

Estimate and optimize recipe cost.

**Backend**

- Add table: `ingredient_prices`
  - `name`
  - `avg_price`
  - `unit`
  - `country`
- Logic: match ingredient → estimate cost, sum total
- AI prompt (for cheaper version): "Make this recipe cheaper while keeping it similar. Constraints: Keep same dish identity. Replace expensive ingredients only."

**Frontend**

- Show: "Estimated cost: X PLN"
- Button: "Make cheaper"

**Edge cases**

- Missing price → fallback estimate
- Regional differences

**MVP**

- Static price table (manual or mock)

---

## 7. Family Mode

**Goal**

Support multiple people with constraints.

**Backend**

- Table: `household_members`
  - `id`
  - `user_id`
  - `name`
  - `diet`
  - `allergens`

**UX**

- Settings → "Household"
- Add members
- Toggle: "Apply to all recipes"

**AI prompt**

```
Adapt recipe for a household:

Members:
- Adult: no restrictions
- Child: no spicy
- Child: dairy-free

Return one recipe that works for everyone.
```

**Edge cases**

- Conflicting diets → show warning

**MVP**

- Max 5 members
- No per-person portions yet

---

## 8. Fridge Scan

**Goal**

Upload image → detect ingredients → suggest recipes.

**Backend**

- Endpoint: `POST /scan-fridge`
- AI prompt (vision): "List all visible food items in this image. Return: ingredient name, confidence."
- Then: given these ingredients `{list}`, suggest 3 recipes.

**Frontend**

- Upload button
- Show detected ingredients
- "Fix mistakes" editable list

**Edge cases**

- Wrong detection → must allow edit
- Low-quality image

**MVP**

- No real-time camera
- Single image upload

---

## 12. Replace Entire Recipe

**Goal**

One-click full transformation.

**UX**

- Buttons: "Make faster", "Make cheaper", "Kid-friendly"

**AI prompt**

```
Rewrite this recipe.

Goal: {goal}

Keep:
- same dish identity

Change:
- ingredients
- steps
- cooking method if needed
```

**Backend**

- Store as new variant (like diet versions)

**MVP**

- 3 preset buttons only

---

## 13. Cooking Time Optimizer

**Goal**

Reduce total cooking time via parallelization.

**AI prompt**

```
Optimize this recipe to minimize total cooking time.

Rules:
- Use parallel steps when possible
- Keep result similar

Return:
- new steps
- total estimated time
```

**Frontend**

- Button: "Optimize time"
- Show "before vs after"

**Edge cases**

- Some recipes can't be optimized

**MVP**

- No timeline visualization

---

## 14. Real-world Constraints Mode

**Goal**

Adapt recipes to constraints like time/tools.

**UX**

- User selects: time limit, tools (1 pan, no oven, etc.)

**AI prompt**

```
Adapt recipe with constraints:

- Max time: 20 min
- Tools: 1 pan only
- No oven

Keep dish recognizable.
```

**Backend**

- Store constraints in request only (no DB needed)

**MVP**

- Preset constraints only

---

## 15. Onboarding Upgrade

**Goal**

Show value in first 30 seconds.

**UX flow**

- After signup: ask "3 foods you love"
- Immediately generate 3 recipes
- Show "Your personalized recipes"

**AI prompt**

```
User likes: {foods}

Generate 3 recipes tailored to them.
```

**Frontend**

- Replace empty cookbook screen

**MVP**

- No long forms
- Skip allowed

---

## 16. Gamification (light)

**Goal**

Increase retention without being annoying.

**Backend**

- Table: `user_stats`
  - `cooking_streak`
  - `recipes_cooked`
  - `money_saved_estimate`
- Logic: increment when recipe opened in cook mode or marked "cooked"

**Frontend**

- Small badges: "3-day streak", "Saved 120 PLN"

**MVP**

- No levels
- No notifications yet
