/**
 * Consistent API error message handling. Use t() for i18n fallback.
 * @param {unknown} err - Error from api client (may have .message, .status)
 * @param {(key: string) => string} t - LanguageContext t()
 * @param {string} [fallbackKey='somethingWentWrong'] - Translation key if no message
 * @returns {string}
 */
export function getErrorMessage(err, t, fallbackKey = 'somethingWentWrong') {
  const msg = err?.message
  if (typeof msg === 'string' && msg.trim()) return msg.trim()
  return t(fallbackKey) || 'Something went wrong.'
}
