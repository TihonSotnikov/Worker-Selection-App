from enum import IntEnum


class ShiftPreference(IntEnum):
    """
    Предпочтения кандидата по графику работы.

    Используется для ML-моделирования совместимости.

    Attributes
    ----------
    DAY_ONLY : int
        Предпочтительны только дневные смены.
    NIGHT_ONLY : int
        Предпочтительны только ночные смены.
    ANY : int
        Готовность работать в любое время.
    """

    DAY_ONLY = 0
    NIGHT_ONLY = 1
    ANY = 2


class RiskLevel(IntEnum):
    """
    Уровень риска увольнения сотрудника (Retention Risk).

    Рассчитывается ML-моделью на основе совокупности факторов.

    Attributes
    ----------
    LOW : int
        Низкий риск (скорее всего останется).
    MEDIUM : int
        Средний риск.
    HIGH : int
        Высокий риск (скорее всего уволится).
    """

    LOW = 0
    MEDIUM = 1
    HIGH = 2
