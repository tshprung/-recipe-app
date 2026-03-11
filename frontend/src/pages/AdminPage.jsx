import { useState, useEffect } from 'react'

const BASE = (import.meta.env.VITE_API_URL ?? '') + '/api'
const ADMIN_TOKEN_KEY = 'recipe_app_admin_token'

function formatApiErrorDetail(detail) {
  if (!detail) return 'Request failed'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    // FastAPI / Pydantic often returns [{ loc, msg, type, ... }]
    const msgs = detail
      .map(d => {
        if (!d) return null
        if (typeof d === 'string') return d
        if (d.msg) {
          const loc = Array.isArray(d.loc) ? d.loc.join('.') : null
          return loc ? `${loc}: ${d.msg}` : d.msg
        }
        return null
      })
      .filter(Boolean)
    if (msgs.length) return msgs.join('; ')
  }
  try {
    return JSON.stringify(detail)
  } catch {
    return String(detail)
  }
}

function toIntOr(value, fallback) {
  const n = typeof value === 'number' ? value : parseInt(String(value ?? ''), 10)
  return Number.isFinite(n) ? n : fallback
}

async function adminRequest(token, path, options = {}) {
  const headers = { 'Content-Type': 'application/json', 'X-Admin-Token': token, ...options.headers }
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (res.status === 204) return null
  const data = await res.json().catch(() => ({ detail: 'Request failed' }))
  if (!res.ok) throw new Error(formatApiErrorDetail(data.detail))
  return data
}

export default function AdminPage() {
  const [token, setToken] = useState(() => localStorage.getItem(ADMIN_TOKEN_KEY) || '')
  const [users, setUsers] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [editingLimit, setEditingLimit] = useState({})
  const [limitInput, setLimitInput] = useState({})
  const [usedInput, setUsedInput] = useState({})
  const [actionLoading, setActionLoading] = useState(null)

  useEffect(() => {
    if (token) localStorage.setItem(ADMIN_TOKEN_KEY, token)
  }, [token])

  function fetchUsers() {
    if (!token.trim()) return
    setLoading(true)
    setError(null)
    adminRequest(token, '/admin/users')
      .then(data => setUsers(data))
      .catch(e => {
        setError(e.message || 'Failed to load users')
        setUsers(null)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (token.trim()) fetchUsers()
    else setUsers(null)
  }, [token])

  function handleSetCredits(userId, newLimit, newUsed) {
    const user = users?.find(u => u.id === userId)
    if (!user) return
    setActionLoading(userId)
    const payload = { email: user.email, new_limit: newLimit }
    if (newUsed !== undefined && newUsed !== '') payload.transformations_used = parseInt(newUsed, 10)
    adminRequest(token, '/admin/upgrade-user', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
      .then(() => {
        setEditingLimit(prev => ({ ...prev, [userId]: false }))
        fetchUsers()
      })
      .catch(e => setError(e.message || 'Failed to update'))
      .finally(() => setActionLoading(null))
  }

  function handleBlock(userId) {
    setActionLoading(userId)
    adminRequest(token, `/admin/users/${userId}/block`, { method: 'POST' })
      .then(() => fetchUsers())
      .catch(e => setError(e.message || 'Failed to block'))
      .finally(() => setActionLoading(null))
  }

  function handleUnblock(userId) {
    setActionLoading(userId)
    adminRequest(token, `/admin/users/${userId}/unblock`, { method: 'POST' })
      .then(() => fetchUsers())
      .catch(e => setError(e.message || 'Failed to unblock'))
      .finally(() => setActionLoading(null))
  }

  function handleDelete(userId) {
    const user = users?.find(u => u.id === userId)
    if (!user || !window.confirm(`Delete user ${user.email} and all their data?`)) return
    setActionLoading(userId)
    adminRequest(token, `/admin/users/${userId}`, { method: 'DELETE' })
      .then(() => setUsers(prev => (prev || []).filter(u => u.id !== userId)))
      .catch(e => setError(e.message || 'Failed to delete'))
      .finally(() => setActionLoading(null))
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-stone-800 mb-4">Admin</h1>
      <div className="mb-4">
        <label className="block text-sm font-semibold text-stone-600 mb-1">Admin token</label>
        <input
          type="password"
          value={token}
          onChange={e => setToken(e.target.value)}
          placeholder="Enter admin token"
          className="w-full max-w-md border border-stone-200 rounded-lg px-3 py-2 text-sm"
        />
      </div>
      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-2">
          {error}
        </div>
      )}
      {loading && <p className="text-stone-500 text-sm">Loading users…</p>}
      {!token.trim() && <p className="text-stone-500 text-sm">Enter admin token to list users.</p>}
      {users && users.length === 0 && <p className="text-stone-500 text-sm">No users.</p>}
      {users && users.length > 0 && (
        <div className="overflow-x-auto border border-stone-200 rounded-xl bg-white">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-stone-200 bg-stone-50">
                <th className="px-4 py-3 font-semibold text-stone-700">Email</th>
                <th className="px-4 py-3 font-semibold text-stone-700">Used / Limit</th>
                <th className="px-4 py-3 font-semibold text-stone-700">Tier</th>
                <th className="px-4 py-3 font-semibold text-stone-700">Verified</th>
                <th className="px-4 py-3 font-semibold text-stone-700">Blocked</th>
                <th className="px-4 py-3 font-semibold text-stone-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className="border-b border-stone-100 hover:bg-stone-50/50">
                  <td className="px-4 py-3 text-stone-800">{u.email}</td>
                  <td className="px-4 py-3">
                    {editingLimit[u.id] ? (
                      <span className="flex items-center gap-2 flex-wrap">
                        <input
                          type="number"
                          value={limitInput[u.id] ?? u.transformations_limit}
                          onChange={e => setLimitInput(prev => ({ ...prev, [u.id]: e.target.value }))}
                          className="w-20 border border-stone-200 rounded px-2 py-1 text-sm"
                          placeholder="Limit"
                        />
                        <input
                          type="number"
                          value={usedInput[u.id] ?? u.transformations_used}
                          onChange={e => setUsedInput(prev => ({ ...prev, [u.id]: e.target.value }))}
                          className="w-16 border border-stone-200 rounded px-2 py-1 text-sm"
                          placeholder="Used"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            handleSetCredits(
                              u.id,
                              toIntOr(limitInput[u.id], u.transformations_limit),
                              usedInput[u.id] !== undefined && usedInput[u.id] !== ''
                                ? toIntOr(usedInput[u.id], u.transformations_used)
                                : undefined
                            )
                          }
                          disabled={actionLoading === u.id}
                          className="text-amber-600 hover:underline text-xs font-medium"
                        >
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingLimit(prev => ({ ...prev, [u.id]: false }))}
                          className="text-stone-500 hover:underline text-xs"
                        >
                          Cancel
                        </button>
                      </span>
                    ) : (
                      <span>
                        {u.transformations_used} / {u.transformations_limit === -1 ? '∞' : u.transformations_limit}
                        <button
                          type="button"
                          onClick={() => setEditingLimit(prev => ({ ...prev, [u.id]: true }))}
                          className="ml-2 text-amber-600 hover:underline text-xs"
                        >
                          Edit
                        </button>
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-stone-600">{u.account_tier}</td>
                  <td className="px-4 py-3">{u.is_verified ? 'Yes' : 'No'}</td>
                  <td className="px-4 py-3">{u.is_blocked ? 'Yes' : 'No'}</td>
                  <td className="px-4 py-3 space-x-2">
                    {u.is_blocked ? (
                      <button
                        type="button"
                        onClick={() => handleUnblock(u.id)}
                        disabled={actionLoading === u.id}
                        className="text-emerald-600 hover:underline text-xs font-medium"
                      >
                        Unblock
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleBlock(u.id)}
                        disabled={actionLoading === u.id}
                        className="text-amber-600 hover:underline text-xs font-medium"
                      >
                        Block
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDelete(u.id)}
                      disabled={actionLoading === u.id}
                      className="text-red-600 hover:underline text-xs font-medium"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
