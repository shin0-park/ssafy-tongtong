const absoluteUrlPattern = /^https?:\/\//i

export function resolveMediaUrl(url) {
  if (!url || typeof url !== 'string') {
    return ''
  }

  if (absoluteUrlPattern.test(url)) {
    return url
  }

  if (url.startsWith('/')) {
    const apiBase = import.meta.env.VITE_API_BASE_URL || '/api/v1'

    if (apiBase.startsWith('http')) {
      return new URL(url, apiBase).toString()
    }

    return url
  }

  return url
}
