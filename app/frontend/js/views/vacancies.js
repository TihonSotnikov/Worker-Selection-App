import { api, getCatalog } from '../api.js';
import { h, money, pct, signed, yearsFrom } from '../ui.js';

function vacancyCard(v, catalog) {
  const requirements = [
    ...v.requirements.map((r) => h('li', {}, h('span', {}, catalog.skills[r.skill]), h('span', {}, yearsFrom(r.min_years)))),
    ...v.certificates.map((c) =>
      h('li', {}, h('span', {}, catalog.certificates[c.kind]), h('span', {}, c.min_level ? `от ${c.min_level}` : 'обязательно')),
    ),
  ];
  return h(
    'a',
    { class: 'card vacancy-card', href: `#/vacancy/${v.id}` },
    h('div', { class: 'row' }, h('span', { class: 'chip accent' }, catalog.professions[v.profession]), h('span', { class: 'chip' }, catalog.shifts[v.shift])),
    h('h2', {}, v.title),
    h('div', { class: 'vacancy-meta' }, h('span', {}, `${v.company} · ${catalog.zones[v.zone]}`), h('span', { class: 'salary' }, money(v.salary))),
    h('ul', { class: 'req-list' }, requirements),
    h('div', { class: 'row muted small' }, `Кандидатов в базе: ${v.candidates_total}`, h('span', { style: { marginLeft: 'auto' } }, 'Шорт-лист →')),
  );
}

function insightsCard(status) {
  const { insights, ml } = status;
  const baseline = insights.baseline * 100;
  const rows = insights.scenarios.map((sc) =>
    h(
      'div',
      { class: 'bar-row' },
      h('span', {}, sc.label),
      h(
        'div',
        { class: 'bar-track', role: 'img', 'aria-label': `${sc.label}: удержание ${pct(sc.retention)}` },
        h('div', { class: 'bar-baseline', style: { left: `${baseline}%` } }),
        h('div', { class: 'bar-fill', style: { width: `${sc.retention * 100}%` } }),
        h('span', { class: 'bar-value', style: { left: `${sc.retention * 100}%` } }, `${pct(sc.retention)} (${signed(sc.delta)})`),
      ),
    ),
  );
  return h(
    'section',
    { class: 'card' },
    h(
      'div',
      { class: 'card-head' },
      h(
        'div',
        { class: 'section-title' },
        h('h2', {}, 'Что выучила модель удержания'),
        h(
          'p',
          { class: 'muted small' },
          `Типичный подходящий кандидат остаётся на 90 дней с вероятностью ${pct(insights.baseline)}. `,
          'Ниже — как меняется прогноз, если поменять один фактор. Вертикальная черта — типичный кандидат.',
        ),
      ),
      h('span', { class: 'pill' }, `CatBoost · ROC-AUC ${ml.roc_auc.toFixed(2)}`),
    ),
    h('div', { class: 'bar-list' }, rows),
  );
}

export async function renderVacancies(root) {
  const [vacancies, catalog, status] = await Promise.all([api('/vacancies'), getCatalog(), api('/status')]);
  root.replaceChildren(
    h(
      'div',
      { class: 'stack' },
      h(
        'section',
        { class: 'hero' },
        h('h1', {}, 'Подбор рабочих на производство'),
        h(
          'p',
          {},
          'ИИ-рекрутер проводит интервью, проверяет навыки по цитатам из ответов и собирает шорт-лист по двум осям — ',
          'навыки и комфорт — с прогнозом, что человек не уйдёт в первые 90 дней.',
        ),
      ),
      h(
        'div',
        { class: 'steps' },
        h('div', { class: 'step' }, h('b', {}, '1 · Интервью'), h('span', {}, 'Вопросы по навыкам вакансии и условиям: смены, дорога, зарплата, быт.')),
        h('div', { class: 'step' }, h('b', {}, '2 · Проверка'), h('span', {}, 'Локальная LLM извлекает навыки со стажем; навык засчитывается, только если есть цитата.')),
        h('div', { class: 'step' }, h('b', {}, '3 · Шорт-лист'), h('span', {}, 'Ранжирование по навыкам и комфорту плюс прогноз удержания с объяснением.')),
      ),
      h('div', { class: 'card-head' }, h('h2', {}, 'Вакансии'), h('span', { class: 'muted small' }, `${vacancies.length} открытых позиций · машиностроение`)),
      h('div', { class: 'vacancy-grid' }, vacancies.map((v) => vacancyCard(v, catalog))),
      insightsCard(status),
      h('footer', { class: 'page-footer' }, 'Все компании, кандидаты и персональные данные вымышлены и сгенерированы для демонстрации.'),
    ),
  );
}
