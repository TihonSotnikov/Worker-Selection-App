import { api } from '../api.js';
import { backLink, h, overlay, storageGet, storageSet, toast } from '../ui.js';

function speak(text, enabled) {
  if (!enabled || !('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'ru-RU';
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang?.toLowerCase().startsWith('ru'));
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
}

function bubble(message) {
  const isCandidate = message.role === 'candidate';
  return h(
    'div',
    { class: `bubble ${isCandidate ? 'candidate' : 'assistant'}` },
    isCandidate ? null : h('div', { class: 'bubble-role' }, '🔊 ИИ-рекрутер'),
    message.text,
  );
}

export async function renderInterview(root, vacancyId, interviewId) {
  let [interview, vacancy] = await Promise.all([api(`/interviews/${interviewId}`), api(`/vacancies/${vacancyId}`)]);
  let voice = storageGet('interview-voice', true);
  let busy = false;

  const chat = h('div', { class: 'chat', 'aria-live': 'polite' });
  const progressFill = h('div', { class: 'progress-fill' });
  const progressText = h('span', { class: 'muted small' });
  const footer = h('div', {});

  const voiceToggle = h('input', { type: 'checkbox' });
  voiceToggle.checked = voice;
  voiceToggle.addEventListener('change', () => {
    voice = voiceToggle.checked;
    storageSet('interview-voice', voice);
    if (!voice && 'speechSynthesis' in window) window.speechSynthesis.cancel();
  });

  const answers = () => interview.messages.filter((m) => m.role === 'candidate').length;
  const lastQuestion = () => [...interview.messages].reverse().find((m) => m.role === 'assistant')?.text ?? '';

  async function send(textarea, button) {
    const text = textarea.value.trim();
    if (!text || busy) return;
    busy = true;
    button.disabled = true;
    try {
      interview = await api(`/interviews/${interviewId}/answer`, { method: 'POST', json: { text } });
      render();
      speak(lastQuestion(), voice);
    } catch (e) {
      toast(e.message);
    } finally {
      busy = false;
      button.disabled = false;
    }
  }

  async function finish() {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    const progress = overlay('Разбираю ответы', 'Локальная модель извлекает навыки, цитаты и профиль комфорта. Обычно 15–40 секунд.');
    try {
      interview = await api(`/interviews/${interviewId}/finish`, { method: 'POST' });
      location.hash = `#/vacancy/${vacancyId}/candidate/${interview.candidate_id}`;
    } catch (e) {
      toast(e.message);
    } finally {
      progress.close();
    }
  }

  function composer() {
    const textarea = h('textarea', { rows: 2, placeholder: 'Ответ кандидата… (Enter — отправить, Shift+Enter — новая строка)', 'aria-label': 'Ответ кандидата' });
    const button = h('button', { class: 'button primary', type: 'button' }, 'Ответить');
    button.addEventListener('click', () => send(textarea, button));
    textarea.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        send(textarea, button);
      }
    });
    queueMicrotask(() => textarea.focus());
    const early = answers() > 0 ? h('button', { class: 'link-button small', type: 'button', onclick: finish }, 'Завершить досрочно и проанализировать') : null;
    return h('div', { class: 'stack', style: { gap: '8px' } }, h('div', { class: 'composer' }, textarea, button), early);
  }

  function render() {
    chat.replaceChildren(...interview.messages.map(bubble));
    const done = Math.min(interview.step, interview.total_questions);
    progressFill.style.width = `${(done / interview.total_questions) * 100}%`;
    progressText.textContent =
      interview.status === 'active' ? `Вопрос ${interview.step + 1} из ${interview.total_questions}` : `Все ${interview.total_questions} вопросов пройдены`;

    if (interview.status === 'done' && interview.candidate_id) {
      footer.replaceChildren(
        h('a', { class: 'button primary wide', href: `#/vacancy/${vacancyId}/candidate/${interview.candidate_id}` }, 'Интервью разобрано — открыть отчёт по кандидату'),
      );
    } else if (interview.status === 'ready') {
      // h() отбрасывает null, а replaceChildren превратил бы его в текст «null»
      footer.replaceChildren(
        h(
          'div',
          {},
          h('button', { class: 'button primary wide', type: 'button', onclick: finish }, 'Завершить интервью и проанализировать'),
          interview.error ? h('p', { class: 'muted small', style: { marginTop: '8px' } }, `Прошлая попытка: ${interview.error}`) : null,
        ),
      );
    } else {
      footer.replaceChildren(composer());
    }
    requestAnimationFrame(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }));
  }

  root.replaceChildren(
    h(
      'div',
      { class: 'interview' },
      h(
        'div',
        { class: 'stack', style: { gap: '12px' } },
        backLink(`#/vacancy/${vacancyId}`, `Вакансия: ${vacancy.title}`),
        h('h1', {}, 'Интервью с кандидатом'),
        h(
          'div',
          { class: 'row' },
          h('span', { class: 'chip accent' }, '🎙 Голосовое интервью · симуляция: ответы вводятся текстом'),
          h('label', { class: 'switch' }, voiceToggle, 'Озвучивать вопросы'),
        ),
        h('div', { class: 'progress' }, progressFill),
        progressText,
      ),
      chat,
      footer,
    ),
  );
  render();
  if (interview.status === 'active' && answers() === 0) speak(lastQuestion(), voice);
}
