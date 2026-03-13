/** Recipe detail UI constants. */

export const TAG_COLORS = [
  'bg-amber-100 text-amber-700',
  'bg-orange-100 text-orange-700',
  'bg-rose-100 text-rose-700',
  'bg-emerald-100 text-emerald-700',
  'bg-lime-100 text-lime-700',
  'bg-teal-100 text-teal-700',
]

export const NOTE_META = {
  porcje: { tKey: 'servings', icon: '🍽' },
  czas_przygotowania: { tKey: 'prepTime', icon: '⏱' },
  czas_gotowania: { tKey: 'cookTime', icon: '🔥' },
}

/** Keywords for auto-detecting ingredient content tags (meat, dairy, eggs, fish). */
export const CONTENT_KEYWORDS = [
  { label: 'Contains meat', icon: '🥩', words: ['mięso', 'kurczak', 'wołowina', 'wieprzowina', 'indyk', 'boczek', 'kiełbasa', 'wędlina', 'szynka', 'wątróbka', 'żeberka', 'mielone', 'kotlet', 'schab', 'cielęcina', 'kaczka', 'jagnięcina', 'baranina', 'rostbef', 'meat', 'chicken', 'beef', 'pork'] },
  { label: 'Contains dairy', icon: '🧀', words: ['mleko', 'śmietana', 'śmietanka', 'ser', 'masło', 'jogurt', 'twaróg', 'ricotta', 'mozzarella', 'parmezan', 'kefir', 'maślanka', 'brie', 'camembert', 'feta', 'gouda', 'edam', 'milk', 'cream', 'cheese', 'butter'] },
  { label: 'Contains eggs', icon: '🥚', words: ['jajko', 'jajka', 'jaja', 'żółtko', 'egg'] },
  { label: 'Contains fish', icon: '🐟', words: ['ryba', 'łosoś', 'tuńczyk', 'dorsz', 'śledź', 'makrela', 'sardynka', 'pstrąg', 'karp', 'halibut', 'flądra', 'mintaj', 'krewetki', 'kalmary', 'fish', 'salmon', 'tuna'] },
]
