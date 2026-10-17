const intents = new WeakMap();
const uploads = new WeakMap();
export async function api(path, { method = 'GET', body, key } = {}) {
  const headers = {};
  const csrf = document.cookie.split('; ').find(c => c.startsWith('bvs_csrf='))?.slice(9);
  if (method !== 'GET' && csrf) headers['X-CSRF-Token'] = decodeURIComponent(csrf);
  if (key) headers['Idempotency-Key'] = key;
  if (body && !(body instanceof FormData)) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(body); }
  let response;
  try { response = await fetch('/api/v1' + path, { method, headers, body }); }
  catch { throw new Error('Connection lost. Retry this action to reuse the same request.'); }
  if (response.status === 204) return null;
  const value = await response.json();
  if (!response.ok) { const error = new Error(value.error?.message ?? 'Request failed'); error.details = value.error?.details ?? []; throw error; }
  return value;
}
export async function submit(form, path, body) {
  const hash = JSON.stringify(body);
  let intent = intents.get(form);
  if (!intent || intent.hash !== hash || intent.path !== path) {
    intent = { hash, path, key: crypto.randomUUID() }; intents.set(form, intent);
  }
  const value = await api(path, { method: 'POST', body, key: intent.key });
  intents.delete(form);
  return value;
}
export async function upload(file, purpose) {
  if (uploads.has(file)) return uploads.get(file);
  const body = new FormData(); body.append('file', file); body.append('purpose', purpose);
  const value = await api('/uploads', { method: 'POST', body });
  uploads.set(file, value);
  return value;
}
