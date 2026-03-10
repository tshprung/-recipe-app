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
