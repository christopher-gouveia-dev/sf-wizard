async function request<T>(method: string, path: string, body?: any): Promise<T> {
  const res = await fetch(path.startsWith('/api') ? path : `/api${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  })
  const text = await res.text()
  let json: any = null
  try { json = text ? JSON.parse(text) : null } catch { /* ignore */ }
  if (!res.ok) {
    const msg = (json && (json.detail || json.message)) || text || `HTTP ${res.status}`
    throw new Error(msg)
  }
  return json as T
}

export default {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: any) => request<T>('POST', path, body)
}
