import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const COLORS = { bg: '#111111', card: '#1c1c1c', text: '#F8F8F6' }

export default function TermsPage() {
  const { user, trialToken } = useAuth()
  const backTo = (user || trialToken) ? '/' : '/signin'
  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: COLORS.bg, color: COLORS.text }}>
      <div className="max-w-2xl mx-auto">
        <Link to={backTo} className="inline-block text-sm text-white/70 hover:text-white mb-6">← Back</Link>
        <h1 className="text-2xl font-bold mb-2">Terms of Service</h1>
        <p className="text-white/60 text-sm mb-6">Last updated: {new Date().toLocaleDateString('en-GB')}</p>

        <div className="prose prose-invert prose-sm max-w-none text-white/80 space-y-4">
          <p>This service is provided “as is” without warranties.</p>

          <h2>Acceptable use</h2>
          <ul>
            <li>You agree not to misuse the service or attempt to disrupt it.</li>
            <li>You will not try to access other users’ data or accounts.</li>
          </ul>

          <h2>Accounts</h2>
          <ul>
            <li>We may suspend or terminate accounts at our discretion, including for misuse or abuse.</li>
            <li>You are responsible for keeping your account credentials secure.</li>
          </ul>

          <h2>Your content</h2>
          <p>You are responsible for any content you provide.</p>

          <h2>Contact</h2>
          <p>For questions, contact: <a href="mailto:tshprung@gmail.com">tshprung@gmail.com</a></p>
        </div>
      </div>
    </div>
  )
}
