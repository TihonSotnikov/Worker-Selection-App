"""
Справочники предметной области: профессии, навыки, удостоверения, районы, условия.

Это единственный источник истины для подписей в UI, вопросов интервью,
схемы извлечения LLM и синтетических данных.
"""

from dataclasses import dataclass

from app.core.enums import (
    Amenity,
    CertKind,
    Profession,
    ShiftPreference,
    ShiftSchedule,
    TeamFormat,
    TeamPreference,
    Zone,
)


@dataclass(frozen=True)
class Skill:
    key: str
    label: str
    profession: Profession
    question: str
    evidence_templates: tuple[str, ...]
    # Основы слов, хотя бы одна из которых должна быть в цитате, чтобы она подтверждала навык.
    keywords: tuple[str, ...] = ()


PROFESSION_LABELS: dict[Profession, str] = {
    Profession.CNC: "Оператор станков с ЧПУ",
    Profession.WELDER: "Сварщик",
    Profession.ELECTRO: "Электромеханик",
}

# Базовая рыночная зарплата «на руки» для синтетики, руб.
MARKET_SALARY: dict[Profession, int] = {
    Profession.CNC: 95_000,
    Profession.WELDER: 90_000,
    Profession.ELECTRO: 95_000,
}

_SKILLS: tuple[Skill, ...] = (
    # --- ЧПУ ---
    Skill(
        "cnc_milling",
        "Фрезерная обработка на ЧПУ",
        Profession.CNC,
        "Сколько лет вы работаете на фрезерных станках с ЧПУ? Какие детали делали и какие допуски держали?",
        (
            "На фрезерных с ЧПУ работаю {years}, корпусные детали, допуски до сотки держу.",
            "Последние {years} стою на фрезерной группе, трёхосевая обработка.",
        ),
        ("фрез",),
    ),
    Skill(
        "cnc_turning",
        "Токарная обработка на ЧПУ",
        Profession.CNC,
        "Сколько лет вы работаете на токарных станках с ЧПУ? С какими деталями и материалами?",
        (
            "Токарку на ЧПУ веду {years} — валы, втулки, фланцы.",
            "{years_cap} на токарных с ЧПУ, и серийка, и штучные детали.",
        ),
        ("токар",),
    ),
    Skill(
        "fanuc",
        "Стойки Fanuc",
        Profession.CNC,
        "С какими стойками ЧПУ вы работали? Сколько лет на Fanuc и что делали сами — привязку, правку программ?",
        (
            "На стойках Fanuc {years}, привязку инструмента делаю сам.",
            "Fanuc знаю хорошо, {years} на нём, коррекции и нулевые точки выставляю сам.",
        ),
        ("fanuc", "фанук"),
    ),
    Skill(
        "sinumerik",
        "Стойки Siemens Sinumerik",
        Profession.CNC,
        "Работали ли вы на стойках Siemens Sinumerik? Сколько лет и что умеете на них делать?",
        (
            "С Sinumerik работал {years}, правил программы прямо на стойке.",
            "Sinumerik — {years}, циклы ShopMill знаю.",
        ),
        ("sinumerik", "синумерик", "siemens", "сименс", "shopmill"),
    ),
    Skill(
        "gcode",
        "Программирование УП (G-код)",
        Profession.CNC,
        "Пишете ли вы управляющие программы сами? Сколько лет и насколько сложные?",
        (
            "Программы пишу сам в G-кодах {years}, циклы и подпрограммы.",
            "Управляющие программы составляю сам, опыт {years}.",
        ),
        ("программ", "g-код", "g код", "джи-код", "cam"),
    ),
    Skill(
        "blueprints",
        "Чтение чертежей",
        Profession.CNC,
        "Насколько свободно вы читаете чертежи — допуски, посадки, шероховатость?",
        (
            "Чертежи читаю свободно, {years}, с допусками и посадками разбираюсь.",
            "По чертежам работаю {years}, шероховатость и посадки понимаю.",
        ),
        ("чертеж",),
    ),
    Skill(
        "metrology",
        "Измерительный инструмент",
        Profession.CNC,
        "Каким измерительным инструментом вы пользуетесь для контроля деталей?",
        (
            "Микрометр, штангенциркуль, нутромер — {years}, сам себя контролирую.",
            "Мерительным инструментом пользуюсь {years}, детали сдаю ОТК с первого раза.",
        ),
        ("микрометр", "штанген", "нутромер", "мерител", "измерит", "калибр", "индикатор"),
    ),
    # --- Сварка ---
    Skill(
        "tig",
        "Аргонодуговая сварка (TIG)",
        Profession.WELDER,
        "Сколько лет вы варите аргоном (TIG)? Какие металлы и толщины, какие швы?",
        (
            "Аргоном варю {years}, нержавейка и алюминий, трубы до 5 мм.",
            "TIG — {years}, в основном нержавейка, потолочные швы тоже делаю.",
        ),
        ("tig", "тиг", "аргон"),
    ),
    Skill(
        "mig_mag",
        "Полуавтомат (MIG/MAG)",
        Profession.WELDER,
        "Сколько лет вы работаете полуавтоматом (MIG/MAG)? Какие конструкции варили?",
        (
            "Полуавтоматом варю {years}, металлоконструкции, углы и стыки.",
            "MIG/MAG — {years}, фермы и рамы.",
        ),
        ("полуавтомат", "mig", "mag", "миг"),
    ),
    Skill(
        "mma",
        "Ручная дуговая сварка (MMA)",
        Profession.WELDER,
        "Варите ли вы электродом (ручная дуговая)? Сколько лет и в каких положениях?",
        (
            "Электродом {years}, во всех пространственных положениях.",
            "Ручной дуговой {years}, трубы и металлоконструкции.",
        ),
        ("электрод", "ручн", "mma", "рдс", "дугов"),
    ),
    Skill(
        "stainless",
        "Нержавейка и алюминий",
        Profession.WELDER,
        "Есть ли у вас опыт сварки нержавейки и алюминия? Сколько лет?",
        (
            "С нержавейкой и алюминием {years}, знаю про поддув и подготовку кромок.",
            "Нержавейку варю {years}, пищевое оборудование.",
        ),
        ("нержав", "алюмин", "титан"),
    ),
    # --- Электромеханика ---
    Skill(
        "equipment_repair",
        "Ремонт промышленного оборудования",
        Profession.ELECTRO,
        "Сколько лет вы ремонтируете промышленное оборудование? Какое именно?",
        (
            "Ремонтирую станочное оборудование {years} — и механику, и электрику.",
            "{years_cap} на ремонте прессов и станков.",
        ),
        ("ремонт", "станок", "станк", "оборудован", "разобра", "разбер", "слесар", "механик"),
    ),
    Skill(
        "plc",
        "ПЛК и автоматика",
        Profession.ELECTRO,
        "Работали ли вы с ПЛК и автоматикой? С какими контроллерами и сколько лет?",
        (
            "С ПЛК Siemens и Овен {years}, ошибку по программе найду.",
            "Автоматику обслуживаю {years}, контроллеры Овен.",
        ),
        ("плк", "контроллер", "plc", "автоматик", "овен", "киповец", "кипиа"),
    ),
    Skill(
        "hydraulics",
        "Гидравлика и пневматика",
        Profession.ELECTRO,
        "Есть ли опыт обслуживания гидравлики и пневматики? Сколько лет?",
        (
            "Гидравлику и пневматику обслуживаю {years}, прессы и станки.",
            "Гидростанции ремонтирую {years}.",
        ),
        ("гидравл", "пневм", "гидро"),
    ),
    Skill(
        "electrical_install",
        "Электромонтаж",
        Profession.ELECTRO,
        "Какой у вас опыт электромонтажа — шкафы, кабельные трассы, подключение двигателей?",
        (
            "Электромонтаж {years} — шкафы, трассы, подключение двигателей.",
            "Собираю щиты и шкафы управления {years}.",
        ),
        ("электромонтаж", "монтаж", "шкаф", "щит", "кабел", "электрик", "проводк", "подключ"),
    ),
    Skill(
        "drives",
        "Частотные приводы",
        Profession.ELECTRO,
        "Настраивали ли вы частотные преобразователи? Какие и сколько лет?",
        (
            "Частотники настраиваю {years}, Danfoss и Schneider.",
            "С частотными приводами {years}.",
        ),
        ("частотн", "привод", "преобразовател", "danfoss", "schneider"),
    ),
)

SKILLS: dict[str, Skill] = {skill.key: skill for skill in _SKILLS}


def skills_for(profession: Profession) -> list[Skill]:
    return [skill for skill in _SKILLS if skill.profession == profession]


CERT_LABELS: dict[CertKind, str] = {
    CertKind.GRADE: "Квалификационный разряд",
    CertKind.NAKS: "Аттестация НАКС",
    CertKind.ELSAFETY: "Группа по электробезопасности",
    CertKind.SLINGER: "Удостоверение стропальщика",
}

# Для каких удостоверений важен уровень (разряд / группа).
CERT_HAS_LEVEL: set[CertKind] = {CertKind.GRADE, CertKind.ELSAFETY}

SHIFT_SCHEDULE_LABELS: dict[ShiftSchedule, str] = {
    ShiftSchedule.DAY: "Дневные смены 5/2",
    ShiftSchedule.NIGHT: "Ночные смены",
    ShiftSchedule.ROTATING: "Сменный график 2/2 (день/ночь)",
}

SHIFT_PREFERENCE_LABELS: dict[ShiftPreference, str] = {
    ShiftPreference.DAY_ONLY: "Только дневные смены",
    ShiftPreference.ANY: "Любой график",
    ShiftPreference.NIGHT: "Предпочитает ночные смены",
    ShiftPreference.UNKNOWN: "Не выяснено",
}

TEAM_FORMAT_LABELS: dict[TeamFormat, str] = {
    TeamFormat.TEAM: "Работа в бригаде",
    TeamFormat.SOLO: "Самостоятельная работа",
    TeamFormat.MIXED: "Смешанный формат",
}

TEAM_PREFERENCE_LABELS: dict[TeamPreference, str] = {
    TeamPreference.TEAM: "Предпочитает бригаду",
    TeamPreference.SOLO: "Предпочитает работать один",
    TeamPreference.ANY: "Без разницы",
    TeamPreference.UNKNOWN: "Не выяснено",
}

AMENITY_LABELS: dict[Amenity, str] = {
    Amenity.CANTEEN: "Столовая",
    Amenity.SHOWER: "Душ",
    Amenity.DORMITORY: "Общежитие",
    Amenity.SHUTTLE: "Развозка",
}

ZONE_LABELS: dict[Zone, str] = {
    Zone.CENTER: "Центр",
    Zone.LEFT_BANK: "Левый берег (промзона)",
    Zone.NORTH: "Северный район",
    Zone.SOUTH: "Южный район",
    Zone.SUBURB: "Пригород",
}

# Время в пути между районами, минут: (общественный транспорт, личная машина).
_TRAVEL: dict[frozenset[Zone], tuple[int, int]] = {
    frozenset({Zone.CENTER}): (20, 15),
    frozenset({Zone.LEFT_BANK}): (20, 15),
    frozenset({Zone.NORTH}): (20, 15),
    frozenset({Zone.SOUTH}): (20, 15),
    frozenset({Zone.SUBURB}): (40, 30),
    frozenset({Zone.CENTER, Zone.LEFT_BANK}): (45, 30),
    frozenset({Zone.CENTER, Zone.NORTH}): (40, 25),
    frozenset({Zone.CENTER, Zone.SOUTH}): (45, 30),
    frozenset({Zone.CENTER, Zone.SUBURB}): (80, 50),
    frozenset({Zone.LEFT_BANK, Zone.NORTH}): (70, 45),
    frozenset({Zone.LEFT_BANK, Zone.SOUTH}): (60, 40),
    frozenset({Zone.LEFT_BANK, Zone.SUBURB}): (95, 60),
    frozenset({Zone.NORTH, Zone.SOUTH}): (75, 50),
    frozenset({Zone.NORTH, Zone.SUBURB}): (105, 65),
    frozenset({Zone.SOUTH, Zone.SUBURB}): (70, 45),
}


def travel_minutes(home: Zone, work: Zone, has_car: bool) -> int:
    transit, car = _TRAVEL[frozenset({home, work})]
    return car if has_car else transit


def years_ru(years: float) -> str:
    """Форматирует стаж: «1 год», «3 года», «5 лет», «1,5 года»."""

    if years != int(years):
        return f"{years:g} года".replace(".", ",")
    n = int(years)
    if n % 10 == 1 and n % 100 != 11:
        word = "год"
    elif n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        word = "года"
    else:
        word = "лет"
    return f"{n} {word}"


def years_from_ru(years: float) -> str:
    """Родительный падеж для требований: «от 1 года», «от 3 лет», «от 1,5 года»."""

    if years != int(years):
        return f"от {years:g} года".replace(".", ",")
    n = int(years)
    return f"от {n} года" if n % 10 == 1 and n % 100 != 11 else f"от {n} лет"


def lower_first(text: str) -> str:
    """«Аттестация НАКС» → «аттестация НАКС»: аббревиатуры не портятся."""

    return text[:1].lower() + text[1:]


def roman(n: int) -> str:
    return {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}.get(n, str(n))
