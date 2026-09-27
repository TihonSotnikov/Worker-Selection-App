import { api } from './js/api.js';
import { h, loading } from './js/ui.js';
import { renderCandidate } from './js/views/candidate.js';
import { renderInterview } from './js/views/interview.js';
import { renderVacancies } from './js/views/vacancies.js';
import { renderVacancy } from './js/views/vacancy.js';

const root = document.querySelector('#app');

const ROUTES = [
  [/^#?\/?$/, () => renderVacancies(root)],
  [/^#\/vacancy\/(\d+)$/, (m) => renderVacancy(root, Number(m[1]))],
  [/^#\/vacancy\/(\d+)\/candidate\/(\d+)$/, (m) => renderCandidate(root, Number(m[1]), Number(m[2]))],
  [/^#\/vacancy\/(\d+)\/interview\/(\d+)$/, (m) => renderInterview(root, Number(m[1]), Number(m[2]))],
];

async function route() {
  const hash = location.hash || '#/';
  root.replaceChildren(loading());
  window.scrollTo(0, 0);
  for (const [pattern, view] of ROUTES) {
    const match = hash.match(pattern);
    if (!match) continue;
    try {
      await view(match);
    } catch (e) {
      root.replaceChildren(h('div', { class: 'card empty' }, h('h2', {}, 'Не удалось загрузить страницу'), h('p', {}, e.message), h('p', {}, h('a', { href: '#/' }, 'К списку вакансий'))));
    }
    return;
  }
  root.replaceChildren(h('div', { class: 'card empty' }, 'Страница не найдена. ', h('a', { href: '#/' }, 'К вакансиям')));
}

async function refreshStatus() {
  const row = document.querySelector('#statusRow');
  try {
    const status = await api('/status');
    const llm = status.llm;
    row.replaceChildren(
      h(
        'span',
        { class: 'pill', title: llm.detail },
        h('span', { class: `dot ${llm.available ? 'good' : 'critical'}` }),
        llm.available ? `LLM ${llm.model} · готова` : `LLM недоступна: ${llm.detail}`,
      ),
      h('span', { class: 'pill' }, h('span', { class: 'dot good' }), `Модель удержания · ROC-AUC ${status.ml.roc_auc.toFixed(2)}`),
    );
    if (!llm.available) setTimeout(refreshStatus, 15000);
  } catch {
    row.replaceChildren(h('span', { class: 'pill' }, h('span', { class: 'dot critical' }), 'Сервер недоступен'));
    setTimeout(refreshStatus, 15000);
  }
}

window.addEventListener('hashchange', route);
route();
refreshStatus();
