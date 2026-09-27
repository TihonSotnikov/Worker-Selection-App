export async function api(path, { method = 'GET', json, form } = {}) {
  const options = { method, headers: {} };
  if (json !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(json);
  }
  if (form) options.body = form;

  let response;
  try {
    response = await fetch(`/api${path}`, options);
  } catch {
    throw new Error('Сервер недоступен. Проверьте, что приложение запущено.');
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // пустой или не-JSON ответ
  }
  if (!response.ok) {
    const detail = payload?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join('; ')
          : `Ошибка ${response.status}`;
    throw new Error(message);
  }
  return payload;
}

let catalogPromise;
export function getCatalog() {
  catalogPromise ??= api('/catalog');
  return catalogPromise;
}
