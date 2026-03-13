import { createContext, useContext, useEffect, useState } from 'react'
import { LANG_STORAGE_KEY } from '../constants/storageKeys'
import { translations } from '../locales/translations'


const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    try {
      const stored = localStorage.getItem(LANG_STORAGE_KEY)
      if (stored === 'en' || stored === 'he' || stored === 'pl') return stored
    } catch (_) {}
    return 'en'
  })

  useEffect(() => {
    try {
      localStorage.setItem(LANG_STORAGE_KEY, lang)
    } catch (_) {}
    const html = document.documentElement
    html.setAttribute('lang', lang === 'he' ? 'he' : lang === 'pl' ? 'pl' : 'en')
    html.setAttribute('dir', lang === 'he' ? 'rtl' : 'ltr')
  }, [lang])

  function setLang(l) {
    if (l === 'en' || l === 'he' || l === 'pl') setLangState(l)
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
