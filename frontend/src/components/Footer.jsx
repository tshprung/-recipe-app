import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="border-t border-white/10 mt-8">
      <div className="max-w-5xl mx-auto px-3 sm:px-4 py-6 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between text-xs text-white/60">
        <div className="flex gap-4">
          <Link to="/privacy" className="hover:text-white transition">Privacy Policy</Link>
          <Link to="/terms" className="hover:text-white transition">Terms of Service</Link>
        </div>
        <div>© {new Date().getFullYear()} Recipe App</div>
      </div>
    </footer>
  )
}

