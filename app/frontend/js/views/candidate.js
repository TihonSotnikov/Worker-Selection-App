import { api, getCatalog } from '../api.js';
import { backLink, CERT_STATUS, COMFORT_STATUS, h, pct, points, RISK, signed, SKILL_STATUS, SOURCE_LABELS, status } from '../ui.js';

const QUOTE_CAPTIONS = {
  found: '✓ цитата найдена в ответах кандидата',
  not_found: 'модель привела цитату, которой нет в ответах, — навык не засчитан',
  off_topic: 'цитата есть в ответах, но не про этот навык — навык не засчитан',
};

function quote(text, verified, status, synthetic) {
  if (!text) return null;
  const caption = synthetic ? (verified ? '✓ подтверждено в симулированном интервью' : 'заявлено без подтверждения') : QUOTE_CAPTIONS[status] ?? '';
  return h(
    'div',
    {},
    h('blockquote', { class: `quote${verified ? ' verified' : ''}` }, `«${text}»`),
    h('span', { class: 'muted small' }, caption),
  );
}

function skillsCard(report) {
  const synthetic = report.source === 'synthetic';
  const skillRows = report.skill_checks.map((c) =>
    h('tr', {}, h('td', {}, h('strong', {}, c.label)), h('td', {}, status(SKILL_STATUS[c.status])), h('td', {}, c.note, quote(c.evidence, c.verified, c.evidence_status, synthetic))),
  );
  const certRows = report.cert_checks.map((c) =>
    h('tr', {}, h('td', {}, h('strong', {}, c.label)), h('td', {}, status(CERT_STATUS[c.status])), h('td', {}, c.note, c.evidence ? h('blockquote', { class: 'quote' }, `«${c.evidence}»`) : null)),
  );
  const head = h('thead', {}, h('tr', {}, h('th', {}, 'Требование'), h('th', {}, 'Результат'), h('th', {}, 'Детали')));
  return h(
    'section',
    { class: 'card' },
    h('div', { class: 'card-head' }, h('h2', {}, 'Проверка навыков и удостоверений')),
    h('div', { class: 'table-wrap' }, h('table', {}, head, h('tbody', {}, skillRows, certRows))),
  );
}

function comfortCard(report) {
  return h(
    'section',
    { class: 'card' },
    h('div', { class: 'card-head' }, h('h2', {}, 'Профиль комфорта'), h('span', { class: 'muted small' }, 'что важно кандидату и что предлагает вакансия')),
    h(
      'div',
      { class: 'table-wrap' },
      h(
        'table',
        {},
        h('thead', {}, h('tr', {}, h('th', {}, 'Критерий'), h('th', {}, 'Кандидат'), h('th', {}, 'Вакансия'), h('th', {}, 'Совпадение'))),
        h(
          'tbody',
          {},
          report.comfort.map((c) =>
            h('tr', {}, h('td', {}, h('strong', {}, c.label)), h('td', {}, c.candidate), h('td', {}, c.vacancy), h('td', {}, status(COMFORT_STATUS[c.status]))),
          ),
        ),
      ),
    ),
  );
}

function factorList(factors, positive) {
  if (!factors.length) {
    return h('p', { class: 'muted' }, positive ? 'Заметных плюсов модель не нашла.' : 'Существенных рисков не найдено.');
  }
  const spec = positive ? { cls: 'good', icon: '▲' } : { cls: 'critical', icon: '▼' };
  return h(
    'ul',
    { class: 'factor-list' },
    factors.map((f) => h('li', { class: 'factor' }, status(spec, ''), h('span', {}, f.text), h('span', { class: 'impact' }, signed(f.impact)))),
  );
}

function retentionCard(report) {
  return h(
    'section',
    { class: 'card' },
    h(
      'div',
      { class: 'card-head' },
      h(
        'div',
        { class: 'section-title' },
        h('h2', {}, 'Почему такой прогноз удержания'),
        h('p', { class: 'muted small' }, 'Число — на сколько процентных пунктов фактор сдвигает вероятность остаться на 90 дней (SHAP-вклад модели).'),
      ),
    ),
    h(
      'div',
      { class: 'grid-2' },
      h('div', { class: 'stack', style: { gap: '10px' } }, h('h3', {}, 'Риски'), factorList(report.risks, false)),
      h('div', { class: 'stack', style: { gap: '10px' } }, h('h3', {}, 'Сильные стороны'), factorList(report.strengths, true)),
    ),
  );
}

function rankText(data) {
  const r = data.report;
  if (!r.rank) return 'Не прошёл обязательные требования вакансии';
  if (r.rank <= 5) return `Место ${r.rank} в шорт-листе`;
  return `Место ${r.rank} из ${data.shortlist_size} прошедших проверку навыков`;
}

export async function renderCandidate(root, vacancyId, candidateId) {
  const [data, catalog] = await Promise.all([api(`/vacancies/${vacancyId}/candidates/${candidateId}`), getCatalog()]);
  const { vacancy: v, candidate: c, report: r } = data;

  root.replaceChildren(
    h(
      'div',
      { class: 'stack' },
      backLink(`#/vacancy/${vacancyId}`, `Шорт-лист: ${v.title}`),
      h(
        'section',
        { class: 'report-head' },
        h(
          'div',
          { class: 'stack', style: { gap: '10px' } },
          h('div', { class: 'row' }, h('span', { class: 'chip accent' }, SOURCE_LABELS[c.source]), h('span', { class: 'chip' }, catalog.professions[c.profile.profession])),
          h('h1', {}, r.full_name),
          h('p', { class: 'muted' }, `${rankText(data)} · вакансия «${v.title}», ${v.company}`),
        ),
        h('div', { class: 'hero-number' }, h('b', {}, points(r.final_score)), h('span', { class: 'muted small' }, 'итоговый балл из 100')),
      ),
      h(
        'div',
        { class: 'grid-3' },
        h('div', { class: 'card stat' }, h('span', { class: 'stat-label' }, 'Навыки'), h('span', { class: 'stat-value' }, `${points(r.tech_score)} / 100`), h('span', { class: 'muted small' }, 'подтверждённые навыки и удостоверения')),
        h('div', { class: 'card stat' }, h('span', { class: 'stat-label' }, 'Комфорт'), h('span', { class: 'stat-value' }, `${points(r.comfort_score)} / 100`), h('span', { class: 'muted small' }, 'график, дорога, зарплата, условия')),
        h('div', { class: 'card stat' }, h('span', { class: 'stat-label' }, 'Удержание 90 дней'), h('span', { class: 'stat-value' }, pct(r.retention)), status(RISK[r.risk_level])),
      ),
      r.summary ? h('section', { class: 'card' }, h('div', { class: 'card-head' }, h('h2', {}, 'Кратко')), h('p', {}, r.summary)) : null,
      skillsCard(r),
      comfortCard(r),
      retentionCard(r),
      r.clarify.length
        ? h('section', { class: 'card' }, h('div', { class: 'card-head' }, h('h2', {}, 'Что уточнить у кандидата')), h('ul', { class: 'plain-list' }, r.clarify.map((item) => h('li', {}, item))))
        : null,
      c.transcript
        ? h('section', { class: 'card' }, h('details', {}, h('summary', {}, 'Расшифровка интервью'), h('div', { class: 'transcript' }, c.transcript)))
        : null,
    ),
  );
}
