import { Link } from 'react-router-dom'

const COLORS = { bg: '#111111', card: '#1c1c1c', text: '#F8F8F6' }

export default function TermsPage() {
  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: COLORS.bg, color: COLORS.text }}>
      <div className="max-w-2xl mx-auto">
        <Link to="/signin" className="inline-block text-sm text-white/70 hover:text-white mb-6">← Back to login</Link>
        <h1 className="text-2xl font-bold mb-4">Terms of Service</h1>
        <div className="prose prose-invert prose-sm max-w-none text-white/80 space-y-4">
          <p>Welcome to Intelligent Kitchen Helper (myrecipes.cloud). By using this service you agree to use it responsibly and in line with these terms.</p>
          <p>We reserve the right to update these terms. Continued use after changes constitutes acceptance.</p>
          <p>For questions, contact: tshprung@gmail.com</p>
        </div>
      </div>
    </div>
  )
}
