const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, { code = 'request_failed', status = 0, files = [] } = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.files = files
  }
}

export async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options)
  } catch {
    throw new ApiError('We could not reach the photo service. You can try again when the local server is running.', { code: 'service_unavailable' })
  }

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload?.detail || {}
    throw new ApiError(detail.message || 'Something went wrong while adding your photos.', { code: detail.code, status: response.status, files: detail.files })
  }
  return payload
}

export { API_BASE_URL }
