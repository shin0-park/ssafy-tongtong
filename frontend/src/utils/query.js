export function cleanParams(params = {}, allowedKeys = []) {
  const allowed = new Set(allowedKeys)

  return Object.entries(params).reduce((nextParams, [key, value]) => {
    if (!allowed.has(key)) {
      return nextParams
    }

    if (value === undefined || value === null || value === '') {
      return nextParams
    }

    if (Array.isArray(value)) {
      const values = value.map((item) => String(item).trim()).filter(Boolean)

      if (!values.length) {
        return nextParams
      }

      nextParams[key] = values.join(',')
      return nextParams
    }

    nextParams[key] = value
    return nextParams
  }, {})
}

export function readStringQuery(route, key, fallback = '') {
  const value = route.query[key]

  if (Array.isArray(value)) {
    return value[0] || fallback
  }

  return typeof value === 'string' ? value : fallback
}

export function readCommaQuery(route, key) {
  return readStringQuery(route, key)
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
}

export function toCommaParam(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean).join(',') || undefined
  }

  return value || undefined
}

export function normalizeOrdering(value, allowedValues = [], fallback = allowedValues[0]) {
  return allowedValues.includes(value) ? value : fallback
}

export function readPageQuery(route) {
  const page = Number.parseInt(route.query.page, 10)
  const pageSize = Number.parseInt(route.query.page_size, 10)

  return {
    page: Number.isFinite(page) && page > 0 ? page : 1,
    page_size: Number.isFinite(pageSize) && pageSize > 0 ? pageSize : undefined,
  }
}

export function sanitizeInternalRedirect(redirect, fallback = '/') {
  if (typeof redirect !== 'string' || !redirect.startsWith('/')) {
    return fallback
  }

  if (redirect.startsWith('//')) {
    return fallback
  }

  const lowerRedirect = redirect.toLowerCase()

  if (lowerRedirect.startsWith('/http://') || lowerRedirect.startsWith('/https://')) {
    return fallback
  }

  return redirect
}
