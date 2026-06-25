export function buildMultipartPayload(payload = {}, fileFields = {}) {
  const formData = new FormData()

  Object.entries(payload).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }

    if (Array.isArray(value) || typeof value === 'object') {
      formData.append(key, JSON.stringify(value))
      return
    }

    formData.append(key, value)
  })

  Object.entries(fileFields).forEach(([key, files]) => {
    const nextFiles = Array.isArray(files) ? files : [files]

    nextFiles.filter(Boolean).forEach((file) => {
      formData.append(key, file)
    })
  })

  return formData
}

export function hasFiles(files) {
  return Array.isArray(files) ? files.some(Boolean) : Boolean(files)
}

export const DEFAULT_MAX_IMAGE_SIZE_MB = 10
export const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

export function findInvalidImage(files, options = {}) {
  const nextFiles = Array.isArray(files) ? files.filter(Boolean) : [files].filter(Boolean)
  const allowedTypes = options.allowedTypes ?? ALLOWED_IMAGE_TYPES
  const maxSizeMb = options.maxSizeMb ?? DEFAULT_MAX_IMAGE_SIZE_MB
  const maxSizeBytes = maxSizeMb * 1024 * 1024

  return (
    nextFiles.find((file) => !allowedTypes.includes(file.type) || file.size > maxSizeBytes) ?? null
  )
}
