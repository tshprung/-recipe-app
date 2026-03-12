import { Link } from 'react-router-dom'

export function TrialExhaustedModal({ open, onClose }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" onClick={onClose}>
      <div
        className="rounded-2xl shadow-xl max-w-md w-full p-6 bg-stone-900 border border-stone-700 text-stone-100"
        onClick={e => e.stopPropagation()}
      >
        <p className="text-lg font-semibold">Free trial used</p>
        <p className="mt-2 text-stone-400 text-sm">
          You've used your 5 free recipes. Create an account to save your recipes and get more.
        </p>
        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          <Link
            to="/login?tab=register"
            className="inline-flex justify-center rounded-xl px-4 py-3 text-sm font-semibold text-black bg-amber-400 hover:bg-amber-300 transition"
          >
            Create account
          </Link>
          <Link
            to="/login"
            className="inline-flex justify-center rounded-xl px-4 py-3 text-sm font-semibold ring-1 ring-stone-500 hover:bg-stone-700 transition"
          >
            Log in
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex justify-center rounded-xl px-4 py-3 text-sm font-medium text-stone-400 hover:text-stone-200 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
