export const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/+$/, '');

export class ApiError extends Error {
  code: string;
  details?: any;

  constructor(message: string, code = 'API_ERROR', details?: any) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = details;
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('aairo_access_token');
  
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401 && !endpoint.includes('/auth/login')) {
    localStorage.removeItem('aairo_access_token');
    localStorage.removeItem('aairo_refresh_token');
    window.location.href = '/login';
    throw new ApiError('Session expired. Please log in again.', 'UNAUTHORIZED');
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const apiDetail = data?.error?.message || data?.detail;
    const errorMsg = Array.isArray(apiDetail)
      ? apiDetail.map((item) => {
        const field = Array.isArray(item?.loc) ? item.loc.filter((part: unknown) => part !== 'body').join('.') : '';
        return [field, item?.msg].filter(Boolean).join(': ');
      }).filter(Boolean).join('; ') || 'The request could not be validated.'
      : typeof apiDetail === 'string' ? apiDetail
        : apiDetail && typeof apiDetail === 'object' ? 'The request could not be completed.'
          : 'An unexpected error occurred';
    const requestId = data?.request_id || response.headers.get('X-Request-ID');
    const messageWithReference = response.status >= 500 && requestId
      ? `${errorMsg} (Reference: ${requestId})`
      : errorMsg;
    throw new ApiError(messageWithReference, data?.error?.code || 'REQUEST_FAILED', data?.error?.details);
  }

  return data?.data !== undefined ? data.data : data;
}
