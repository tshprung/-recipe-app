import { createContext, useContext, useEffect, useState } from 'react'
import { translations } from '../locales/translations'


const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  // UI language is fixed to English for now.
  const [lang, setLangState] = useState('en')

  useEffect(() => {
    const html = document.documentElement
    html.setAttribute('lang', 'en')
    html.setAttribute('dir', 'ltr')
  }, [lang])

  function setLang(l) {
    // kept for backwards-compat with existing callers; UI language is fixed to English.
    if (l === 'en') setLangState('en')
  }

  function t(key, vars = {}) {
    const raw = translations[lang]?.[key] ?? translations.en[key] ?? key
    if (typeof raw !== 'string') return key
    return Object.entries(vars).reduce((s, [k, v]) => s.replace(new RegExp(`{{${k}}}`, 'g'), String(v)), raw)
  }

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider')
  return ctx
}
