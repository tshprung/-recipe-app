/**
 * Hash password client-side (SHA-256 + base64) so the raw password is never sent.
 * Must match backend _prehash so verification works.
 */
export async function hashPasswordForTransport(password) {
  const msgBuffer = new TextEncoder().encode(password)
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer)
  const hashArray = new Uint8Array(hashBuffer)
  const binary = String.fromCharCode(...hashArray)
  return btoa(binary)
}
