"""
Сценарий интервью: вопросы собираются из требований и условий вакансии.

Покрывает обязательные компоненты ТЗ: проверку профессиональных навыков
(вопрос на каждый обязательный навык) и сбор «мягких» критериев — график,
дорога, зарплата, бытовые условия, формат работы, стабильность.
"""

from app.core.catalog import CERT_LABELS, SHIFT_SCHEDULE_LABELS, SKILLS, ZONE_LABELS, lower_first
from app.core.schemas import InterviewMessage, VacancyData

MAX_SKILL_QUESTIONS = 3

CLOSING = "Спасибо, это все вопросы! Нажмите «Завершить интервью» — я разберу ответы и покажу результат рекрутеру."


def build_script(vacancy: VacancyData) -> list[dict[str, str]]:
    questions = [
        {
            "key": "intro",
            "text": (
                f"Здравствуйте! Я виртуальный рекрутер компании «{vacancy.company}». "
                f"Мы подбираем сотрудника на вакансию «{vacancy.title}». Интервью займёт 5–7 минут. "
                "Как вас зовут и сколько лет вы работаете по специальности?"
            ),
        }
    ]
    for req in vacancy.requirements[:MAX_SKILL_QUESTIONS]:
        questions.append({"key": f"skill:{req.skill}", "text": SKILLS[req.skill].question})

    if vacancy.certificates:
        names = ", ".join(lower_first(CERT_LABELS[c.kind]) for c in vacancy.certificates)
        cert_text = f"Какие у вас есть действующие удостоверения? Для этой вакансии важны: {names}. Когда продлевали?"
    else:
        cert_text = "Какие у вас есть удостоверения — разряд, допуски? Они действующие?"
    questions.append({"key": "certificates", "text": cert_text})

    questions += [
        {
            "key": "shift",
            "text": (
                f"График на этой вакансии: {lower_first(SHIFT_SCHEDULE_LABELS[vacancy.shift])}. "
                "Как вы относитесь к такому графику и к ночным сменам?"
            ),
        },
        {
            "key": "commute",
            "text": (
                f"Производство находится в районе «{ZONE_LABELS[vacancy.zone]}». Где вы живёте и сколько "
                "времени займёт дорога? Есть ли своя машина? Сколько максимум готовы тратить на дорогу в одну сторону?"
            ),
        },
        {"key": "salary", "text": "Какую зарплату на руки вы ожидаете?"},
        {
            "key": "conditions",
            "text": (
                "Что для вас важно в бытовых условиях: столовая, душ, общежитие, развозка? "
                "И как вам удобнее работать — в бригаде или самостоятельно?"
            ),
        },
        {"key": "history", "text": "Сколько мест работы вы сменили за последние пять лет и почему уходили?"},
    ]
    return questions


def format_transcript(messages: list[InterviewMessage]) -> str:
    lines = []
    for message in messages:
        role = "Кандидат" if message.role == "candidate" else "Рекрутер"
        lines.append(f"{role}: {message.text.strip()}")
    return "\n\n".join(lines)
