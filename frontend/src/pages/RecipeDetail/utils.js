import { variantLabelKey } from '../../constants/recipes'
import { CONTENT_KEYWORDS } from './constants'

/** Parse leading number from ingredient amount (e.g. "2", "1/2", "2 1/2 cups", "1.5") -> number or null */
export function parseAmountLeading(value) {
  if (value == null) return null
  const s = String(value).trim()
  const match = s.match(/^(\d+)\s+(\d+)\/(\d+)|^(\d+)\/(\d+)|^(\d+(?:\.\d+)?)/)
  if (!match) return null
  if (match[1] !== undefined) return parseInt(match[1], 10) + parseInt(match[2], 10) / parseInt(match[3], 10)
  if (match[4] !== undefined) return parseInt(match[4], 10) / parseInt(match[5], 10)
  return parseFloat(match[6])
}

/** Scale ingredient line by factor; supports string or { amount, name } */
export function scaleIngredientLine(ing, factor) {
  if (factor === 1) return ing
  if (typeof ing === 'object' && ing !== null) {
    const amount = ing.amount != null ? String(ing.amount).trim() : ''
    const n = parseAmountLeading(amount)
    if (n != null) {
      const scaled = Math.round(n * factor * 100) / 100
      return { ...ing, amount: String(scaled) }
    }
    return ing
  }
  const str = String(ing)
  const n = parseAmountLeading(str)
  if (n == null) return str
  const scaled = Math.round(n * factor * 100) / 100
  const rest = str.replace(/^[\d\s\/.]+/, '').trim()
  return rest ? `${scaled} ${rest}` : String(scaled)
}

export function variantDisplayLabel(variantType, t) {
  const parts = (variantType || '').split(',').map(s => s.trim()).filter(Boolean)
  if (parts.length === 0) return ''
  if (parts.length === 1) return t(variantLabelKey(parts[0]))
  return parts.map(p => t(variantLabelKey(p))).join(' + ')
}

export function detectContentTags(ingredients) {
  const text = (ingredients || [])
    .map(ing => (typeof ing === 'object' ? `${ing.amount ?? ''} ${ing.name ?? ''}` : ing))
    .join(' ')
    .toLowerCase()
  return CONTENT_KEYWORDS.filter(cat => cat.words.some(w => text.includes(w)))
}
