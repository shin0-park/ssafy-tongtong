export function normalizeApiError(error) {
  if (!error) {
    return {
      status: null,
      message: '알 수 없는 오류가 발생했습니다.',
      fields: null,
    }
  }

  const response = error.response
  const data = response?.data

  if (typeof data?.detail === 'string') {
    return {
      status: response.status,
      message: data.detail,
      fields: null,
    }
  }

  if (data && typeof data === 'object') {
    return {
      status: response?.status ?? null,
      message: '입력값을 확인해주세요.',
      fields: data,
    }
  }

  if (error.code === 'ECONNABORTED') {
    return {
      status: null,
      message: '요청 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.',
      fields: null,
    }
  }

  return {
    status: response?.status ?? null,
    message: error.message || '요청을 처리하지 못했습니다.',
    fields: null,
  }
}

export function extractErrorMessage(error, fallback = '요청을 처리하지 못했습니다.') {
  return normalizeApiError(error).message || fallback
}
