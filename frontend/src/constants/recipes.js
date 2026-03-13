/** Dish types, diet/variant options, and time filters shared across Discover, Onboarding, WhatCanIMake, RecipeDetail. */

export const DISH_TYPES = [
  'pasta', 'pizza', 'chicken', 'beef', 'soups', 'fish', 'salads', 'baking', 'breakfast',
  'vegetarian', 'desserts', 'stews', 'grilling',
]

/** Diet options: key is API value, labelKey is LanguageContext key for t(labelKey). */
export const DIET_OPTIONS = [
  { key: 'vegetarian', labelKey: 'vegetarian' },
  { key: 'vegan', labelKey: 'vegan' },
  { key: 'gluten_free', labelKey: 'glutenFree' },
  { key: 'dairy_free', labelKey: 'dairyFree' },
  { key: 'kosher', labelKey: 'kosher' },
  { key: 'halal', labelKey: 'halal' },
  { key: 'nut_free', labelKey: 'nutFree' },
  { key: 'low_sodium', labelKey: 'lowSodium' },
]

/** Adaptation variant options (same keys as diet; used in RecipeDetail tabs/badges). */
export const VARIANT_OPTIONS = DIET_OPTIONS

/** Badge styling per variant type for RecipeDetail. */
export const VARIANT_BADGE = {
  original: { labelKey: 'original', cls: 'bg-stone-100 text-stone-500' },
  vegetarian: { labelKey: 'vegetarian', cls: 'bg-emerald-100 text-emerald-700' },
  vegan: { labelKey: 'vegan', cls: 'bg-emerald-100 text-emerald-700' },
  dairy_free: { labelKey: 'dairyFree', cls: 'bg-sky-100 text-sky-700' },
  gluten_free: { labelKey: 'glutenFree', cls: 'bg-violet-100 text-violet-700' },
  kosher: { labelKey: 'kosher', cls: 'bg-blue-100 text-blue-700' },
  halal: { labelKey: 'halal', cls: 'bg-teal-100 text-teal-700' },
  nut_free: { labelKey: 'nutFree', cls: 'bg-amber-100 text-amber-700' },
  low_sodium: { labelKey: 'lowSodium', cls: 'bg-rose-100 text-rose-700' },
}

/** Discover page: max time filter options. */
export const TIME_OPTIONS = [
  { value: null, labelKey: 'anyTime' },
  { value: 30, labelKey: 'under30Min' },
  { value: 60, labelKey: 'under60Min' },
]

/** Map variant key to LanguageContext key (for keys that differ, e.g. dairy_free -> dairyFree). */
export function variantLabelKey(key) {
  if (key === 'dairy_free') return 'dairyFree'
  if (key === 'gluten_free') return 'glutenFree'
  if (key === 'nut_free') return 'nutFree'
  if (key === 'low_sodium') return 'lowSodium'
  return key
}
