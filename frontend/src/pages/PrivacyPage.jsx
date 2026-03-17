import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const COLORS = { bg: '#111111', card: '#1c1c1c', text: '#F8F8F6' }

export default function PrivacyPage() {
  const { user, trialToken } = useAuth()
  const backTo = (user || trialToken) ? '/' : '/signin'
  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: COLORS.bg, color: COLORS.text }}>
      <div className="max-w-2xl mx-auto">
        <Link to={backTo} className="inline-block text-sm text-white/70 hover:text-white mb-6">← Back</Link>
        <h1 className="text-2xl font-bold mb-2">Privacy Policy</h1>
        <p className="text-white/60 text-sm mb-6">Last updated: {new Date().toLocaleDateString('en-GB')}</p>

        <div className="prose prose-invert prose-sm max-w-none text-white/80 space-y-4">
          <p>
            We collect basic information such as your email, account data, and usage of the application to provide and improve our service.
          </p>
          <p>
            We may also collect technical information such as IP address and browser type for security and analytics purposes.
          </p>

          <h2>What we collect</h2>
          <ul>
            <li><strong>Account data</strong>: email address, authentication details, and basic profile/preferences.</li>
            <li><strong>Content you provide</strong>: recipes, shopping lists, and any text you enter into the app.</li>
            <li><strong>Usage data</strong>: how you use features (for example, which screens are visited, clicks, and errors).</li>
            <li><strong>Technical data</strong>: IP address, device and browser information, and logs needed to keep the service secure.</li>
          </ul>

          <h2>Why we collect it</h2>
          <ul>
            <li>To provide the service (create accounts, save recipes, generate meal plans, etc.).</li>
            <li>To personalize your experience (language and preference settings).</li>
            <li>To improve reliability and performance.</li>
            <li>To prevent abuse and protect the service.</li>
          </ul>

          <h2>Data sharing</h2>
          <p>
            We do not sell your personal data. Some data may be processed by third-party providers strictly to operate the service
            (for example hosting, logging/analytics, and AI providers used for recipe generation).
          </p>

          <h2>Your rights (access and deletion)</h2>
          <p>
            You can request access to or deletion of your data at any time by contacting us at <a href="mailto:tshprung@gmail.com">tshprung@gmail.com</a>.
          </p>

          <h2>How to delete your data</h2>
          <p>
            You can delete your account and all associated data at any time from your account settings:
            go to <strong>Settings</strong> → <strong>Delete account</strong> and follow the confirmation steps.
            If you cannot access your account, contact <a href="mailto:tshprung@gmail.com">tshprung@gmail.com</a>.
          </p>

          <h2>Contact</h2>
          <p>
            If you have questions about privacy, contact: <a href="mailto:tshprung@gmail.com">tshprung@gmail.com</a>
          </p>
        </div>
      </div>
    </div>
  )
}
