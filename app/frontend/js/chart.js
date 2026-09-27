// Точечный график «Навыки × Комфорт». Цвет точки — риск ухода (статусная палитра,
// всегда вместе с подписью в легенде и подсказке), полая точка — не прошёл
// обязательные требования, цифра — место в шорт-листе.

import { h, pct, points, RISK } from './ui.js';

const SVG_NS = 'http://www.w3.org/2000/svg';
const W = 720;
const H = 380;
const M = { top: 16, right: 24, bottom: 52, left: 60 };
const STATUS_VAR = { good: 'var(--good)', warning: 'var(--warning)', critical: 'var(--critical)' };

function s(tag, attrs = {}, ...children) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  for (const child of children) el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  return el;
}

// Нижняя граница оси подстраивается под данные (для точечного графика ноль не обязателен).
// Берутся только границы с ровным шагом делений: 0/25, 20/20, 60/10.
function domainMin(values) {
  const low = Math.min(...values) - 3;
  return [60, 20, 0].find((candidate) => candidate <= low) ?? 0;
}

function scales(reports) {
  const xMin = domainMin(reports.map((r) => r.tech_score));
  const yMin = domainMin(reports.map((r) => r.comfort_score));
  const x = (v) => M.left + ((v - xMin) / (100 - xMin)) * (W - M.left - M.right);
  const y = (v) => H - M.bottom - ((v - yMin) / (100 - yMin)) * (H - M.top - M.bottom);
  const ticks = (min) => Array.from({ length: 5 }, (_, i) => Math.round(min + ((100 - min) * i) / 4));
  return { x, y, xTicks: ticks(xMin), yTicks: ticks(yMin), xMin, yMin };
}

// Совпадающие точки (например, несколько кандидатов со 100/100) раздвигаются по кругу.
function positions(reports, x, y) {
  const groups = new Map();
  for (const r of reports) {
    const key = `${Math.round(x(r.tech_score) / 10)}:${Math.round(y(r.comfort_score) / 10)}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r);
  }
  const result = new Map();
  for (const group of groups.values()) {
    group.forEach((r, i) => {
      const angle = (2 * Math.PI * i) / group.length + Math.PI;
      const radius = group.length > 1 ? 12 : 0;
      result.set(r.candidate_id, {
        cx: x(r.tech_score) + radius * Math.cos(angle),
        cy: y(r.comfort_score) + radius * Math.sin(angle),
      });
    });
  }
  return result;
}

// Подписи мест: направления перебираются начиная с «прочь от ближайшей соседней точки»,
// берётся первое, где подпись не задевает ни точки, ни уже поставленные подписи.
const LABEL_DIRECTIONS = [-0.25, -0.75, 0.25, 0.75, 0, 1, -0.5, 0.5].map((k) => k * Math.PI);

function angleGap(a, b) {
  const d = Math.abs(a - b) % (2 * Math.PI);
  return d > Math.PI ? 2 * Math.PI - d : d;
}

function directionsFor(cx, cy, dots) {
  const others = dots.filter((d) => d.cx !== cx || d.cy !== cy);
  if (!others.length) return LABEL_DIRECTIONS;
  const nearest = others.reduce((a, b) => (Math.hypot(a.cx - cx, a.cy - cy) <= Math.hypot(b.cx - cx, b.cy - cy) ? a : b));
  if (Math.hypot(nearest.cx - cx, nearest.cy - cy) > 45) return LABEL_DIRECTIONS;
  const away = Math.atan2(cy - nearest.cy, cx - nearest.cx);
  return [...LABEL_DIRECTIONS].sort((a, b) => angleGap(a, away) - angleGap(b, away));
}

function placeLabels(labeled, dots) {
  const placed = new Map();
  for (const { id, cx, cy } of labeled) {
    let best = null;
    const directions = directionsFor(cx, cy, dots);
    for (const distance of [15, 22, 30]) {
      for (const angle of directions) {
        const lx = cx + distance * Math.cos(angle);
        const ly = cy + distance * Math.sin(angle);
        if (lx < M.left + 6 || lx > W + 4 || ly < 2 || ly > H - M.bottom - 6) continue;
        const hitsDot = dots.some((d) => Math.hypot(d.cx - lx, d.cy - ly) < 11);
        const hitsLabel = [...placed.values()].some((l) => Math.hypot(l.lx - lx, l.ly - ly) < 14);
        if (!hitsDot && !hitsLabel) {
          best = { lx, ly };
          break;
        }
      }
      if (best) break;
    }
    placed.set(id, best ?? { lx: cx + 12, ly: cy - 12 });
  }
  return placed;
}

function tooltipContent(r) {
  const rows = [
    ['Итоговый балл', points(r.final_score)],
    ['Навыки', points(r.tech_score)],
    ['Комфорт', points(r.comfort_score)],
    ['Удержание 90 дней', `${pct(r.retention)} · ${RISK[r.risk_level].label.toLowerCase()}`],
    ['Место', r.rank ? (r.rank <= 5 ? `${r.rank} в шорт-листе` : `${r.rank} среди прошедших`) : 'не прошёл требования'],
  ];
  return [
    h('div', { class: 'tooltip-title' }, r.full_name),
    ...rows.map(([label, value]) => h('div', { class: 'tooltip-row' }, h('span', {}, label), h('b', {}, value))),
  ];
}

export function scatter(reports, shortlistIds, onSelect) {
  const wrap = h('div', { class: 'chart-wrap' });
  const tooltip = h('div', { class: 'tooltip hidden', role: 'tooltip' });
  const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, role: 'group', 'aria-label': 'Кандидаты по осям навыков и комфорта' });

  const { x, y, xTicks, yTicks, xMin, yMin } = scales(reports);
  for (const t of xTicks) {
    svg.append(
      s('line', { x1: x(t), x2: x(t), y1: y(yMin), y2: y(100), stroke: 'var(--grid)', 'stroke-width': 1 }),
      s('text', { x: x(t), y: y(yMin) + 20, 'text-anchor': 'middle', 'font-size': 12, fill: 'var(--muted)' }, t),
    );
  }
  for (const t of yTicks) {
    svg.append(
      s('line', { x1: x(xMin), x2: x(100), y1: y(t), y2: y(t), stroke: 'var(--grid)', 'stroke-width': 1 }),
      s('text', { x: x(xMin) - 10, y: y(t) + 4, 'text-anchor': 'end', 'font-size': 12, fill: 'var(--muted)' }, t),
    );
  }
  svg.append(
    s('line', { x1: x(xMin), x2: x(100), y1: y(yMin), y2: y(yMin), stroke: 'var(--axis)', 'stroke-width': 1 }),
    s('text', { x: (x(xMin) + x(100)) / 2, y: H - 8, 'text-anchor': 'middle', 'font-size': 13, fill: 'var(--text-2)' }, 'Навыки, баллы →'),
    s(
      'text',
      { x: -(y(yMin) + y(100)) / 2, y: 16, transform: 'rotate(-90)', 'text-anchor': 'middle', 'font-size': 13, fill: 'var(--text-2)' },
      'Комфорт, баллы →',
    ),
  );

  const place = positions(reports, x, y);
  const labels = placeLabels(
    reports.filter((r) => shortlistIds.has(r.candidate_id)).sort((a, b) => a.rank - b.rank).map((r) => ({ id: r.candidate_id, ...place.get(r.candidate_id) })),
    [...place.values()],
  );
  const ordered = [...reports].sort((a, b) => Number(shortlistIds.has(a.candidate_id)) - Number(shortlistIds.has(b.candidate_id)));

  for (const r of ordered) {
    const { cx, cy } = place.get(r.candidate_id);
    const inShortlist = shortlistIds.has(r.candidate_id);
    const color = STATUS_VAR[RISK[r.risk_level].cls];
    const mark = s('g', {
      class: 'dot-mark',
      tabindex: 0,
      role: 'button',
      'aria-label': `${r.full_name}: навыки ${points(r.tech_score)}, комфорт ${points(r.comfort_score)}, удержание ${pct(r.retention)}`,
    });
    mark.append(s('circle', { cx, cy, r: 12, fill: 'transparent' }));
    mark.append(
      s('circle', {
        class: 'dot-visible',
        cx,
        cy,
        r: inShortlist ? 7 : 5.5,
        fill: r.passes_requirements ? color : 'var(--surface)',
        stroke: r.passes_requirements ? 'var(--surface)' : 'var(--muted)',
        'stroke-width': 2,
      }),
    );
    if (inShortlist) {
      const { lx, ly } = labels.get(r.candidate_id);
      mark.append(
        s('text', { x: lx, y: ly, 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': 12, 'font-weight': 700, fill: 'var(--text)' }, r.rank),
      );
    }

    const show = () => {
      tooltip.replaceChildren(...tooltipContent(r));
      tooltip.classList.remove('hidden');
      const box = svg.getBoundingClientRect();
      const scale = box.width / W;
      const left = cx * scale + 14;
      tooltip.style.left = `${Math.min(left, box.width - 210)}px`;
      tooltip.style.top = `${Math.max(0, cy * scale - 20)}px`;
    };
    const hide = () => tooltip.classList.add('hidden');
    mark.addEventListener('pointerenter', show);
    mark.addEventListener('pointerleave', hide);
    mark.addEventListener('focus', show);
    mark.addEventListener('blur', hide);
    mark.addEventListener('click', () => onSelect(r));
    mark.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        onSelect(r);
      }
    });
    svg.append(mark);
  }

  const legend = h(
    'div',
    { class: 'chart-legend' },
    ...['low', 'medium', 'high'].map((level) =>
      h('span', { class: 'legend-item' }, h('span', { class: `dot ${RISK[level].cls}` }), RISK[level].label),
    ),
    h('span', { class: 'legend-item' }, h('span', { class: 'legend-ring' }), 'Не прошёл обязательные требования'),
    h('span', { class: 'legend-item' }, h('b', {}, '1–5'), ' место в шорт-листе'),
  );

  wrap.append(svg, tooltip);
  return h('div', {}, wrap, legend);
}
