from enum import StrEnum


class Profession(StrEnum):
    """Профессии, на которых сфокусирован MVP (отрасль — машиностроение)."""

    CNC = "cnc_operator"
    WELDER = "welder"
    ELECTRO = "electromechanic"


class CertKind(StrEnum):
    """Виды удостоверений, которые проверяются на интервью."""

    GRADE = "grade"
    NAKS = "naks"
    ELSAFETY = "elsafety"
    SLINGER = "slinger"


class ShiftSchedule(StrEnum):
    """График работы на вакансии."""

    DAY = "day"
    NIGHT = "night"
    ROTATING = "rotating"


class ShiftPreference(StrEnum):
    """Отношение кандидата к сменам."""

    DAY_ONLY = "day_only"
    ANY = "any"
    NIGHT = "night"
    UNKNOWN = "unknown"


class TeamFormat(StrEnum):
    """Формат работы на вакансии."""

    TEAM = "team"
    SOLO = "solo"
    MIXED = "mixed"


class TeamPreference(StrEnum):
    """Как кандидату комфортнее работать."""

    TEAM = "team"
    SOLO = "solo"
    ANY = "any"
    UNKNOWN = "unknown"


class Amenity(StrEnum):
    """Бытовые условия на производстве."""

    CANTEEN = "canteen"
    SHOWER = "shower"
    DORMITORY = "dormitory"
    SHUTTLE = "shuttle"


class Zone(StrEnum):
    """Районы условного города, между которыми считается время в пути."""

    CENTER = "center"
    LEFT_BANK = "left_bank"
    NORTH = "north"
    SOUTH = "south"
    SUBURB = "suburb"


class CandidateSource(StrEnum):
    """Откуда в системе появился кандидат."""

    SYNTHETIC = "synthetic"
    INTERVIEW = "interview"
    UPLOAD = "upload"


class CheckStatus(StrEnum):
    """Результат проверки одного требования или условия."""

    OK = "ok"
    PARTIAL = "partial"
    MISSING = "missing"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    """Уровень риска увольнения в первые 90 дней."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
