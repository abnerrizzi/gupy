export const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export class ApiError extends Error {
  constructor(message, { status, body } = {}) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function fetchJSON(path, opts = {}) {
  const { signal, headers, ...rest } = opts;
  const res = await fetch(`${API_URL}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(headers || {}),
    },
    signal,
    ...rest,
  });
  if (res.status === 204) return null;
  let body = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const message = (body && body.error) || `HTTP ${res.status}`;
    throw new ApiError(message, { status: res.status, body });
  }
  return body;
}
