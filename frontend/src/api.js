const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

export async function api(path, { token, ...options } = {}) {
  const headers = { ...(options.headers || {}) };
  const isForm = typeof FormData !== 'undefined' && options.body instanceof FormData;
  if (options.body && !isForm && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${BASE}/api/v1${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = body.detail || body.message || `Request failed (${response.status})`;
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg || 'Invalid input').join(', ') : message);
  }
  return body;
}

export const auth = {
  login: (email, password) => api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (full_name, email, password) => api('/auth/register', { method: 'POST', body: JSON.stringify({ full_name, email, password }) }),
  me: (token) => api('/auth/me', { token }),
};
