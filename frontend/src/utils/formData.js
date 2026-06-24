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
