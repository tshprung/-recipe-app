import { useEffect, useState } from 'react'

const STORAGE_KEY = 'cookie_notice_ok_v1'

export default function CookieNotice() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    try {
      const ok = localStorage.getItem(STORAGE_KEY) === '1'
      if (!ok) setVisible(true)
    } catch (_) {
      setVisible(true)
    }
  }, [])

  if (!visible) return null

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 px-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
      <div className="max-w-3xl mx-auto rounded-2xl border border-white/10 bg-black/70 backdrop-blur px-4 py-3 flex items-center justify-between gap-3">
        <p className="text-xs text-white/80">
          This site uses cookies to ensure proper functionality.
        </p>
        <button
          type="button"
          onClick={() => {
            try {
              localStorage.setItem(STORAGE_KEY, '1')
            } catch (_) {}
            setVisible(false)
          }}
          className="shrink-0 rounded-xl px-4 py-2 text-xs font-semibold bg-amber-400 text-black hover:bg-amber-300 transition"
        >
          OK
        </button>
      </div>
    </div>
  )
}

