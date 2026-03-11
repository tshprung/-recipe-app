import { Link } from 'react-router-dom'

const COLORS = { bg: '#111111', card: '#1c1c1c', text: '#F8F8F6' }

export default function PrivacyPage() {
  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: COLORS.bg, color: COLORS.text }}>
      <div className="max-w-2xl mx-auto">
        <Link to="/login" className="inline-block text-sm text-white/70 hover:text-white mb-6">← Back to login</Link>
        <h1 className="text-2xl font-bold mb-4">Privacy Policy</h1>
        <div className="prose prose-invert prose-sm max-w-none text-white/80 space-y-4">
          <p>We do not sell your data or recipes. Your recipe content and account information are used only to provide and improve the service.</p>
          <p>We store minimal data needed for your account and preferences (e.g. email, language, location settings).</p>
          <p>For questions, contact: tshprung@gmail.com</p>
        </div>
      </div>
    </div>
  )
}
