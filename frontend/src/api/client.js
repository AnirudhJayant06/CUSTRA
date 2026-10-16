export class ApiError extends Error {
  constructor(status, details) {
    super(details?.message || `Request failed (${status})`);
    this.name = 'ApiError';
    this.status = status;
    this.code = details?.code || 'request_failed';
    this.retryable = Boolean(details?.retryable);
    this.fieldErrors = details?.field_errors || {};
  }
}

export async function api(path, { method = 'GET', body, signal, headers = {} } = {}) {
  const response = await fetch(path, {
    method,
    credentials: 'include',
    signal,
    headers: { ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...headers },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  return readResponse(response, path);
}

async function readResponse(response, path) {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && path !== '/api/auth/login' && typeof window !== 'undefined') {
      window.dispatchEvent(new Event('custra:session-expired'));
    }
    throw new ApiError(response.status, payload);
  }
  return payload;
}

export async function upload(path, formData, { signal } = {}) {
  const response = await fetch(path, {
    method: 'POST', credentials: 'include', body: formData, signal,
  });
  return readResponse(response, path);
}
