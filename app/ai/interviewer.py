import logging

logger = logging.getLogger(__name__)


class Interviewer:
    """
    Управляет процессом интервью: выдает вопросы и собирает ответы.
    """

    def __init__(self):
        self.questions = [
            "Расскажите кратко о вашем последнем месте работы.",
            "Почему вы решили сменить сферу деятельности?",
            "Какие условия работы для вас наиболее важны?",
            "Готовы ли вы к ночным сменам и физическим нагрузкам?",
            "Когда вы сможете приступить к работе?",
        ]

    def get_question(self, index: int) -> str | None:
        """Возвращает вопрос по индексу."""
        if 0 <= index < len(self.questions):
            return self.questions[index]
        return None

    def analyze_interview(self, transcriptions: list[str]) -> str:
        """
        Финальный анализ всех ответов через LLM.

        Parameters
        ----------
        transcriptions : List[str]
            Список расшифрованных ответов кандидата.

        Returns
        -------
        str
            Краткое резюме интервью.
        """
        if not transcriptions:
            return "Кандидат не ответил на вопросы."

        # Заглушка: Андрей должен пробросить это в LLM (extractor)
        return "Интервью проведено. Кандидат ответил на " + str(len(transcriptions)) + " вопросов."
