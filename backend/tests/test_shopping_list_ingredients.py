"""Tests for shopping list ingredient normalization and aggregation."""
import pytest

from app.services.shopping_list_ingredients import (
    aggregate_ingredients,
    normalize_ingredient_for_shopping,
    strip_cooking_instructions,
)


def test_strip_cooking_instructions():
    assert strip_cooking_instructions("egg, beaten") == "egg"
    assert strip_cooking_instructions("soaked in water and squeezed") == ""
    assert strip_cooking_instructions("white bread, soaked in water and squeezed") == "white bread"
    assert strip_cooking_instructions("flour for coating") == "flour"
    assert strip_cooking_instructions("salt") == "salt"


def test_normalize_ingredient_for_shopping():
    # "beaten" stripped from name
    assert normalize_ingredient_for_shopping("1", "egg, beaten") == ("1", "egg")
    # "soaked in water and squeezed" stripped
    assert normalize_ingredient_for_shopping("1/2 slice", "white bread, soaked in water and squeezed") == (
        "1/2 slice",
        "white bread",
    )
    # "for coating" → "some" amount
    assert normalize_ingredient_for_shopping("", "flour for coating") == ("some", "flour")
    assert normalize_ingredient_for_shopping("for coating", "flour") == ("some", "flour")


def test_aggregate_same_ingredient():
    # Two "1 egg" → "2 eggs"
    assert aggregate_ingredients(["1 egg", "1 egg"]) == ["2 eggs"]


def test_aggregate_fractional_quantities():
    # Two "1/2 tablespoon salt" → "1 tablespoon salt"
    assert aggregate_ingredients(["1/2 tablespoon salt", "1/2 tablespoon salt"]) == ["1 tablespoon salt"]


def test_aggregate_mixed_keeps_unparseable():
    # "some flour" has no numeric amount, kept as-is
    result = aggregate_ingredients(["1 egg", "1 egg", "some flour"])
    assert "2 eggs" in result
    assert "some flour" in result
    assert len(result) == 2


def test_aggregate_preserves_different_ingredients():
    result = aggregate_ingredients(
        ["1 egg", "1 egg", "1/2 tablespoon salt", "1/2 tablespoon salt", "1/2 slice white bread"]
    )
    assert "2 eggs" in result
    assert "1 tablespoon salt" in result
    assert "1/2 slice white bread" in result
    assert len(result) == 3


def test_strip_prep_and_usage_phrases():
    assert strip_cooking_instructions("onions, finely chopped") == "onions"
    assert strip_cooking_instructions("parsley, finely chopped") == "parsley"
    assert strip_cooking_instructions("pepper, sliced") == "pepper"
    assert strip_cooking_instructions("tomatoes, peeled and chopped") == "tomatoes"
    assert strip_cooking_instructions("olive oil for sauce") == "olive oil"
    assert strip_cooking_instructions("oil for shallow frying") == "oil"


def test_normalize_amount_range():
    assert normalize_ingredient_for_shopping("1 to 1.25 cups", "milk") == ("1.25 cups", "milk")


def test_aggregate_tablespoon_and_teaspoon():
    result = aggregate_ingredients(["1 tablespoon salt", "1/2 teaspoon salt"])
    assert len(result) == 1
    assert "salt" in result[0]
    assert "tablespoon" in result[0].lower()


def test_aggregate_sugar_tablespoons():
    result = aggregate_ingredients(["1/2 tablespoon sugar", "3 tablespoons sugar"])
    assert result == ["3.5 tablespoons sugar"]


def test_strip_minus_a_handful():
    assert strip_cooking_instructions("cilantro, chopped (minus a handful)") == "cilantro"
    assert strip_cooking_instructions("cilantro (kolendra, Polish), chopped (minus a handful)") == "cilantro (kolendra, Polish)"


def test_weight_in_parentheses():
    amount, name = normalize_ingredient_for_shopping("3 tablespoons (45 grams)", "melted butter")
    assert amount == "45 grams"
    assert name == "butter"


def test_minimum_tablespoon():
    result = aggregate_ingredients(["1/4 teaspoon baharat"])
    assert len(result) == 1
    assert "baharat" in result[0]
    assert "0 " not in result[0]
    assert "1 teaspoon" in result[0] or "tablespoon" in result[0]


def test_oil_minimum_one_cup():
    result = aggregate_ingredients(["1/2 cup olive oil"])
    assert len(result) == 1
    assert "oil" in result[0].lower()
    assert "1 cup" in result[0]


def test_merge_onions_and_tomatoes():
    result = aggregate_ingredients(["2 medium onions", "1 onion", "4 ripe tomatoes", "6 tomatoes"])
    assert any("3 onion" in s for s in result)
    assert any("10 tomato" in s for s in result)


def test_plain_water_excluded():
    from app.services.shopping_list_ingredients import _is_plain_water
    result = aggregate_ingredients(["2 cups water", "1 cup water", "1/2 cup milk"])
    assert not any(_is_plain_water(s) for s in result)
    assert any("milk" in s for s in result)
    result2 = aggregate_ingredients(["1 cup coconut water"])
    assert any("coconut water" in s for s in result2)
    assert not _is_plain_water("1 cup coconut water")
    assert _is_plain_water("3 cups water")
