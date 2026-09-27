// Небольшие помощники для сборки DOM. Весь текст вставляется через text-узлы,
// поэтому данные из LLM или файлов не могут внедрить HTML.

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') el.className = value;
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2), value);
    else if (key === 'style' && typeof value === 'object') Object.assign(el.style, value);
    else el.setAttribute(key, value === true ? '' : value);
  }
  append(el, children);
  return el;
}

export function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

export const pct = (x) => `${Math.round(x * 100)}%`;
export const points = (x) => `${Math.round(x)}`;
export const money = (x) => `${Number(x).toLocaleString('ru-RU')} ₽`;
export const signed = (x) => `${x > 0 ? '+' : '−'}${Math.abs(x).toFixed(0)} п.п.`;

export function yearsFrom(years) {
  const n = Number(years);
  if (!Number.isInteger(n)) return `от ${String(n).replace('.', ',')} года`;
  return n % 10 === 1 && n % 100 !== 11 ? `от ${n} года` : `от ${n} лет`;
}

export const RISK = {
  low: { cls: 'good', icon: '✓', label: 'Низкий риск ухода' },
  medium: { cls: 'warning', icon: '!', label: 'Средний риск ухода' },
  high: { cls: 'critical', icon: '✕', label: 'Высокий риск ухода' },
};

export const SKILL_STATUS = {
  ok: { cls: 'good', icon: '✓', label: 'Подтверждён' },
  partial: { cls: 'warning', icon: '!', label: 'Частично' },
  missing: { cls: 'critical', icon: '✕', label: 'Не подтверждён' },
  unknown: { cls: 'neutral', icon: '?', label: 'Не выяснено' },
};

export const CERT_STATUS = {
  ok: { cls: 'good', icon: '✓', label: 'Есть' },
  partial: { cls: 'warning', icon: '!', label: 'Есть замечания' },
  missing: { cls: 'critical', icon: '✕', label: 'Нет' },
  unknown: { cls: 'neutral', icon: '?', label: 'Не выяснено' },
};

export const COMFORT_STATUS = {
  ok: { cls: 'good', icon: '✓', label: 'Подходит' },
  partial: { cls: 'warning', icon: '!', label: 'Частично' },
  missing: { cls: 'critical', icon: '✕', label: 'Не подходит' },
  unknown: { cls: 'neutral', icon: '?', label: 'Не выяснено' },
};

export const SOURCE_LABELS = {
  synthetic: 'Синтетический профиль',
  interview: 'Интервью в системе',
  upload: 'Загруженная расшифровка',
};

export function status(spec, text) {
  return h('span', { class: `status ${spec.cls}` }, h('span', { class: 'icon', 'aria-hidden': 'true' }, spec.icon), text ?? spec.label);
}

export function meter(label, value, display) {
  return h(
    'div',
    { class: 'meter' },
    h('div', { class: 'meter-head' }, h('span', {}, label), h('b', {}, display ?? points(value))),
    h('div', { class: 'meter-track' }, h('div', { class: 'meter-fill', style: { width: `${Math.max(0, Math.min(100, value))}%` } })),
  );
}

export function backLink(href, text) {
  return h('a', { class: 'back', href }, '← ', text);
}

let toastTimer;
export function toast(message) {
  const el = document.querySelector('#toast');
  el.textContent = message;
  el.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add('hidden'), 6000);
}

export function overlay(title, subtitle) {
  const started = Date.now();
  const timer = h('span', { class: 'muted small' }, '0 с');
  const node = h(
    'div',
    { class: 'overlay', role: 'alertdialog', 'aria-live': 'polite' },
    h('div', { class: 'overlay-card' }, h('div', { class: 'spinner' }), h('h2', {}, title), h('p', { class: 'muted' }, subtitle), timer),
  );
  document.body.append(node);
  const interval = setInterval(() => {
    timer.textContent = `${Math.round((Date.now() - started) / 1000)} с`;
  }, 1000);
  return {
    close() {
      clearInterval(interval);
      node.remove();
    },
  };
}

export function loading() {
  return h('div', { class: 'empty' }, h('div', { class: 'spinner', style: { margin: '0 auto 12px' } }), 'Загрузка…');
}

export function storageGet(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value === null ? fallback : JSON.parse(value);
  } catch {
    return fallback;
  }
}

export function storageSet(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // хранилище может быть недоступно (приватный режим) — просто не запоминаем
  }
}
