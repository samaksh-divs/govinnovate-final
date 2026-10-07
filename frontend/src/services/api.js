const TOKEN_KEY = 'gv_token';
const USER_KEY = 'gv_user';

export function getToken() { return localStorage.getItem(TOKEN_KEY); }
export function getUser() {
  try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; }
}
export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}
export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export class ApiError extends Error {
  constructor(status, data) {
    super((data && (data.detail?.message || data.detail)) || `HTTP ${status}`);
    this.status = status;
    this.data = data;
    this.errors = data?.detail?.errors || [];
  }
}

async function request(path, { method = 'GET', body, formData } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const res = await fetch(path, {
    method,
    headers,
    body: formData ? formData : body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && !path.includes('/auth/login')) {
    clearAuth();
    window.dispatchEvent(new Event('gv-logout'));
  }
  let data = null;
  const text = await res.text();
  if (text) { try { data = JSON.parse(text); } catch { data = { detail: text }; } }
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: 'POST', body }),
  postForm: (p, formData) => request(p, { method: 'POST', formData }),
  patch: (p, body) => request(p, { method: 'PATCH', body }),
  del: (p) => request(p, { method: 'DELETE' }),
  // POST a JSON body (content-type: application/json) — used for endpoints that
  // read the body from the parsed JSON payload, not from form encoding.
  postJson: (p, body) => request(p, { method: 'POST', body, json: true }),
};
