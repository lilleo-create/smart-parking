// Browsers may deny access to storage. Keep demo navigation usable for this page lifetime.
const fallback = new Map<string, string | null>()

export function readTabItem(key: string): string | null {
  if (fallback.has(key)) return fallback.get(key) ?? null
  try {
    return sessionStorage.getItem(key)
  } catch {
    return null
  }
}

export function writeTabItem(key: string, value: string | null) {
  try {
    if (value === null) sessionStorage.removeItem(key)
    else sessionStorage.setItem(key, value)
    fallback.delete(key)
  } catch {
    fallback.set(key, value)
  }
}
