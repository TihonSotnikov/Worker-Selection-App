import { api, getCatalog } from '../api.js';
import { scatter } from '../chart.js';
import { backLink, h, meter, money, overlay, pct, points, RISK, SOURCE_LABELS, status, toast, yearsFrom } from '../ui.js';

const ACCEPT = '.txt,.md,.wav,.mp3,.m4a,.ogg,.webm,.flac';

function candidateRow(r, vacancyId) {
  const reason = r.risks[0]
    ? h('span', { class: 'reason' }, '▼ ', r.risks[0].text)
    : r.strengths[0]
      ? h('span', { class: 'reason' }, '▲ ', r.strengths[0].text)
      : null;
  return h(
    'a',
    { class: 'candidate-row', href: `#/vacancy/${vacancyId}/candidate/${r.candidate_id}` },
    h('span', { class: 'rank' }, r.rank),
    h(
      'div',
      { class: 'candidate-name' },
      h('strong', {}, r.full_name),
      h('div', { class: 'row' }, status(RISK[r.risk_level]), r.source !== 'synthetic' ? h('span', { class: 'chip accent' }, SOURCE_LABELS[r.source]) : null),
      reason,
    ),
    h(
      'div',
      { class: 'meters' },
      meter('Навыки', r.tech_score),
      meter('Комфорт', r.comfort_score),
      meter('Удержание', r.retention * 100, pct(r.retention)),
    ),
    h('div', { class: 'final' }, h('b', {}, points(r.final_score)), h('span', { class: 'muted small' }, 'итог')),
  );
}

function statusCell(r, shortlistIds) {
  if (shortlistIds.has(r.candidate_id)) return status({ cls: 'good', icon: '✓' }, 'В шорт-листе');
  if (r.passes_requirements) return status({ cls: 'neutral', icon: '·' }, 'Прошёл, ниже топ-5');
  const missing = r.skill_checks.filter((c) => c.status === 'missing').map((c) => c.label);
  return status({ cls: 'critical', icon: '✕' }, `Не подтверждён: ${missing.join(', ')}`);
}

function candidatesTable(reports, shortlistIds, vacancyId) {
  const open = (r) => {
    location.hash = `#/vacancy/${vacancyId}/candidate/${r.candidate_id}`;
  };
  return h(
    'div',
    { class: 'table-wrap' },
    h(
      'table',
      {},
      h(
        'thead',
        {},
        h('tr', {}, h('th', {}, '#'), h('th', {}, 'Кандидат'), h('th', { class: 'num' }, 'Навыки'), h('th', { class: 'num' }, 'Комфорт'), h('th', { class: 'num' }, 'Удержание'), h('th', { class: 'num' }, 'Итог'), h('th', {}, 'Статус')),
      ),
      h(
        'tbody',
        {},
        reports.map((r) =>
          h(
            'tr',
            { class: 'clickable', onclick: () => open(r) },
            h('td', { class: 'num' }, r.rank ?? '—'),
            h('td', {}, h('a', { href: `#/vacancy/${vacancyId}/candidate/${r.candidate_id}` }, r.full_name)),
            h('td', { class: 'num' }, points(r.tech_score)),
            h('td', { class: 'num' }, points(r.comfort_score)),
            h('td', { class: 'num' }, pct(r.retention)),
            h('td', { class: 'num' }, points(r.final_score)),
            h('td', {}, statusCell(r, shortlistIds)),
          ),
        ),
      ),
    ),
  );
}

async function startInterview(vacancyId, button) {
  button.disabled = true;
  try {
    const interview = await api('/interviews', { method: 'POST', json: { vacancy_id: vacancyId } });
    location.hash = `#/vacancy/${vacancyId}/interview/${interview.id}`;
  } catch (e) {
    toast(e.message);
    button.disabled = false;
  }
}

async function uploadFile(vacancyId, input) {
  const file = input.files[0];
  if (!file) return;
  const isAudio = !/\.(txt|md)$/i.test(file.name);
  const progress = overlay(
    isAudio ? 'Расшифровываю и анализирую запись' : 'Анализирую расшифровку',
    isAudio
      ? 'Сначала распознавание речи, затем разбор ответов локальной моделью. Обычно 1–2 минуты.'
      : 'Локальная модель извлекает навыки, цитаты и профиль комфорта. Обычно 15–40 секунд.',
  );
  try {
    const form = new FormData();
    form.append('file', file);
    const result = await api(`/vacancies/${vacancyId}/upload`, { method: 'POST', form });
    location.hash = `#/vacancy/${vacancyId}/candidate/${result.candidate_id}`;
  } catch (e) {
    toast(e.message);
  } finally {
    progress.close();
    input.value = '';
  }
}

export async function renderVacancy(root, vacancyId) {
  const [data, catalog] = await Promise.all([api(`/vacancies/${vacancyId}/shortlist`), getCatalog()]);
  const v = data.vacancy;
  const reports = [...data.shortlist, ...data.others];
  const shortlistIds = new Set(data.shortlist.map((r) => r.candidate_id));
  const passed = reports.filter((r) => r.passes_requirements).length;

  const interviewButton = h('button', { class: 'button primary', type: 'button' }, '🎙 Провести интервью');
  interviewButton.addEventListener('click', () => startInterview(vacancyId, interviewButton));
  const fileInput = h('input', { type: 'file', accept: ACCEPT });
  fileInput.addEventListener('change', () => uploadFile(vacancyId, fileInput));

  const requirements = [
    ...v.requirements.map((r) => h('li', {}, h('span', {}, catalog.skills[r.skill]), h('span', {}, yearsFrom(r.min_years)))),
    ...v.certificates.map((c) =>
      h('li', {}, h('span', {}, catalog.certificates[c.kind]), h('span', {}, c.min_level ? `уровень от ${c.min_level}` : 'обязательно')),
    ),
  ];
  const conditions = [
    ['График', catalog.shifts[v.shift]],
    ['Зарплата на руки', money(v.salary)],
    ['Район', catalog.zones[v.zone]],
    ['Формат работы', catalog.team_formats[v.team_format]],
    ['Бытовые условия', v.amenities.map((a) => catalog.amenities[a]).join(', ') || '—'],
  ];

  root.replaceChildren(
    h(
      'div',
      { class: 'stack' },
      backLink('#/', 'Все вакансии'),
      h(
        'section',
        { class: 'vacancy-head' },
        h(
          'div',
          { class: 'stack', style: { gap: '10px' } },
          h('div', { class: 'row' }, h('span', { class: 'chip accent' }, catalog.professions[v.profession]), h('span', { class: 'chip' }, catalog.shifts[v.shift])),
          h('h1', {}, v.title),
          h('p', { class: 'muted' }, `${v.company} · ${catalog.zones[v.zone]}. ${v.description}`),
        ),
        h(
          'div',
          { class: 'actions' },
          interviewButton,
          h('label', { class: 'button file-button', title: 'Текст (.txt) или аудио. Примеры — в папке examples/' }, fileInput, 'Загрузить расшифровку или аудио'),
        ),
      ),
      h(
        'div',
        { class: 'grid-2' },
        h('section', { class: 'card' }, h('div', { class: 'card-head' }, h('h2', {}, 'Требования')), h('ul', { class: 'req-list' }, requirements)),
        h(
          'section',
          { class: 'card' },
          h('div', { class: 'card-head' }, h('h2', {}, 'Условия')),
          h('ul', { class: 'req-list' }, conditions.map(([label, value]) => h('li', {}, h('span', {}, label), h('span', {}, value)))),
        ),
      ),
      h(
        'section',
        { class: 'card' },
        h(
          'div',
          { class: 'card-head' },
          h(
            'div',
            { class: 'section-title' },
            h('h2', {}, 'Шорт-лист'),
            h('p', { class: 'muted small' }, `${data.shortlist.length} лучших из ${passed} прошедших проверку навыков · всего кандидатов: ${reports.length}`),
          ),
          h('span', { class: 'pill' }, 'Итог = 40% навыки + 25% комфорт + 35% удержание'),
        ),
        data.shortlist.length
          ? h('div', { class: 'shortlist' }, data.shortlist.map((r) => candidateRow(r, vacancyId)))
          : h('p', { class: 'empty' }, 'Пока никто не прошёл обязательные требования. Проведите интервью или загрузите расшифровку.'),
      ),
      h(
        'section',
        { class: 'card' },
        h(
          'div',
          { class: 'card-head' },
          h(
            'div',
            { class: 'section-title' },
            h('h2', {}, 'Кандидаты по двум осям'),
            h('p', { class: 'muted small' }, 'Навыки — подтверждённые навыки и удостоверения. Комфорт — насколько условия вакансии совпадают с ожиданиями кандидата.'),
          ),
        ),
        scatter(reports, shortlistIds, (r) => {
          location.hash = `#/vacancy/${vacancyId}/candidate/${r.candidate_id}`;
        }),
      ),
      h('section', { class: 'card' }, h('div', { class: 'card-head' }, h('h2', {}, 'Все кандидаты')), candidatesTable(reports, shortlistIds, vacancyId)),
    ),
  );
}
