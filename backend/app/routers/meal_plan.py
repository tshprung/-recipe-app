"""Weekly meal plan: generate, replace day, add all to shopping list."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.meal_plan_ai import generate_single_meal, generate_weekly_meal_plan

router = APIRouter(prefix="/api/meal-plan", tags=["meal-plan"])

_UNLIMITED_QUOTA_EMAIL = "tshprung@gmail.com"


def _has_unlimited_quota(user: models.User) -> bool:
    return (user.email or "").strip().lower() == _UNLIMITED_QUOTA_EMAIL


def _check_and_consume_quota(user: models.User, db: Session) -> None:
    if _has_unlimited_quota(user):
        return
    row = db.execute(select(models.User).where(models.User.id == user.id)).scalar_one()
    if row.transformations_limit != -1 and row.transformations_used >= row.transformations_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You have reached the free recipes limit. Contact the administrator.",
        )
    row.transformations_used += 1
    db.commit()


def _meal_plan_to_out(plan: models.MealPlan) -> schemas.MealPlanOut:
    days_data = plan.data.get("days") or []
    days = [
        schemas.MealPlanDayOut(
            date=d["date"],
            meals=[schemas.MealPlanMealOut(**m) for m in (d.get("meals") or [])],
        )
        for d in days_data
    ]
    return schemas.MealPlanOut(
        id=plan.id,
        start_date=plan.start_date.isoformat() if hasattr(plan.start_date, "isoformat") else str(plan.start_date),
        days=days,
    )


@router.post("/generate", response_model=schemas.MealPlanOut)
def generate_plan(
    payload: schemas.MealPlanGenerateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Generate a 5–7 day meal plan. Requires verified email. Consumes one transformation quota."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before using the app.",
        )
    _check_and_consume_quota(current_user, db)

    start = payload.start_date or date.today().isoformat()
    try:
        start_date = date.fromisoformat(start)
    except ValueError:
        start_date = date.today()

    try:
        days = generate_weekly_meal_plan(
            start_date=start_date.isoformat(),
            num_days=payload.num_days,
            meal_types=payload.meal_types,
            protein_types=payload.protein_types,
            meat_meals_per_week=payload.meat_meals_per_week,
            fish_meals_per_week=payload.fish_meals_per_week,
            diet_filters=payload.diet_filters or current_user.diet_filters or None,
            allergens=payload.allergens if payload.allergens is not None else current_user.allergens or None,
            custom_avoid_text=(
                payload.custom_avoid_text
                if payload.custom_avoid_text is not None
                else current_user.custom_allergens_text
            ),
            household_adults=current_user.household_adults,
            household_kids=current_user.household_kids,
            max_time_minutes=payload.max_time_minutes,
            budget=payload.budget,
            target_language=(current_user.target_language or "").strip() or "en",
            measurement_system=(current_user.measurement_system or "").strip() or "metric",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    if not days:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate a meal plan. Try relaxing filters or try again.",
        )

    plan = models.MealPlan(
        user_id=current_user.id,
        start_date=start_date,
        data={"days": days},
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _meal_plan_to_out(plan)


@router.get("/latest", response_model=schemas.MealPlanOut)
def get_latest(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return the most recent meal plan for the current user."""
    plan = (
        db.query(models.MealPlan)
        .filter(models.MealPlan.user_id == current_user.id)
        .order_by(models.MealPlan.created_at.desc())
        .first()
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No meal plan found.")
    return _meal_plan_to_out(plan)


@router.post("/{plan_id}/replace-day", response_model=schemas.MealPlanOut)
def replace_day(
    plan_id: int,
    payload: schemas.MealPlanReplaceRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Replace the meal at day_index/meal_index with a new AI-generated meal. Consumes one transformation quota."""
    if not current_user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify your email before using the app.")
    plan = db.get(models.MealPlan, plan_id)
    if not plan or plan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found.")

    days_list = plan.data.get("days") or []
    if payload.day_index >= len(days_list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid day index.")
    meals_list = (days_list[payload.day_index].get("meals") or [])
    if payload.meal_index >= len(meals_list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid meal index.")

    _check_and_consume_quota(current_user, db)

    try:
        new_meal = generate_single_meal(
            diet_filters=current_user.diet_filters or None,
            allergens=current_user.allergens or None,
            custom_avoid_text=current_user.custom_allergens_text,
            max_time_minutes=None,
            target_language=(current_user.target_language or "").strip() or "en",
            measurement_system=(current_user.measurement_system or "").strip() or "metric",
            meal_type=(meals_list[payload.meal_index].get("meal_type") or None),
            protein_types=None,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    if not new_meal:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not generate a replacement meal. Try again.",
        )

    # Preserve the meal_type slot (if present) when replacing.
    if isinstance(meals_list[payload.meal_index], dict) and meals_list[payload.meal_index].get("meal_type") and isinstance(new_meal, dict):
        new_meal["meal_type"] = meals_list[payload.meal_index].get("meal_type")
    meals_list[payload.meal_index] = new_meal
    days_list[payload.day_index]["meals"] = meals_list
    plan.data = {"days": days_list}
    db.commit()
    db.refresh(plan)
    return _meal_plan_to_out(plan)


@router.post("/{plan_id}/add-to-shopping-list", response_model=schemas.MealPlanAddToShoppingListOut)
def add_to_shopping_list(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create recipes from the plan's meals and add them all to the user's shopping list."""
    plan = db.get(models.MealPlan, plan_id)
    if not plan or plan.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found.")

    days_list = plan.data.get("days") or []
    if not days_list:
        return schemas.MealPlanAddToShoppingListOut(recipe_ids=[])

    target_lang = (current_user.target_language or "").strip() or "en"
    target_country = (current_user.target_country or "").strip() or "US"
    target_city = (current_user.target_city or "").strip() or ""

    recipe_ids = []
    for day in days_list:
        for meal in (day.get("meals") or []):
            meal = meal or {}
            title = (meal.get("title") or "").strip() or "Meal"
            ingredients = meal.get("ingredients") or []
            steps = meal.get("steps") or []
            raw_input = title + "\n\nIngredients:\n" + "\n".join(f"- {s}" for s in ingredients) + "\n\nSteps:\n" + "\n".join(
                f"{i + 1}. {s}" for i, s in enumerate(steps)
            )
            recipe = models.Recipe(
                user_id=current_user.id,
                trial_session_id=None,
                title_pl=title,
                title_original=title,
                ingredients_pl=ingredients,
                ingredients_original=ingredients,
                steps_pl=steps,
                tags=[],
                collections=[],
                substitutions={},
                notes={},
                raw_input=raw_input,
                detected_language=target_lang,
                target_language=target_lang,
                target_country=target_country,
                target_city=target_city,
            )
            db.add(recipe)
            db.flush()
            recipe_ids.append(recipe.id)

    db.commit()

    # Add each recipe to shopping list (skip if already present)
    for rid in recipe_ids:
        exists = (
            db.query(models.ShoppingListRecipe)
            .filter(
                models.ShoppingListRecipe.user_id == current_user.id,
                models.ShoppingListRecipe.recipe_id == rid,
            )
            .first()
        )
        if not exists:
            db.add(
                models.ShoppingListRecipe(
                    user_id=current_user.id,
                    recipe_id=rid,
                )
            )
    db.commit()

    # Invalidate shopping list cache
    db.query(models.ShoppingListCache).filter(
        models.ShoppingListCache.user_id == current_user.id
    ).delete(synchronize_session=False)
    db.commit()

    return schemas.MealPlanAddToShoppingListOut(recipe_ids=recipe_ids)
