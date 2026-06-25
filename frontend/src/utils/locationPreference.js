const STORAGE_KEY = 'library-outing:last-location'

export function readStoredLocation() {
  try {
    const rawValue = window.sessionStorage.getItem(STORAGE_KEY)
    if (!rawValue) return null
    const parsed = JSON.parse(rawValue)
    const lat = Number(parsed.lat)
    const lng = Number(parsed.lng)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
    return {
      lat: lat.toFixed(7),
      lng: lng.toFixed(7),
    }
  } catch {
    return null
  }
}

export function storeLocation(position) {
  const lat = Number(position?.coords?.latitude ?? position?.lat)
  const lng = Number(position?.coords?.longitude ?? position?.lng)
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null

  const location = {
    lat: lat.toFixed(7),
    lng: lng.toFixed(7),
  }

  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(location))
  } catch {
    // Ignore storage failures; the in-memory caller state can still use the result.
  }

  return location
}

export function clearStoredLocation() {
  try {
    window.sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // No-op.
  }
}
