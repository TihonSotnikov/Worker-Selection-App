FEATURE_COLS = [
    "skills_verified_count",
    "years_experience",
    "age",
    "commute_time_minutes",
    "shift_preference",
    "salary_expectation",
    "has_certifications",
    "education_level",
    "previous_turnovers",
    "family_status",
    "housing_type",
    "has_transport",
]

# Поля, которые официальный /api/analyze сейчас НЕ умеет отдавать.
# Predictor будет подставлять их автоматически, чтобы ML не падал.
FEATURE_DEFAULTS = {
    "age": 35,
    "education_level": 1,
    "previous_turnovers": 1,
    "family_status": 0,
    "housing_type": 1,
    "has_transport": False,
}

EDUCATION_LABELS = {
    0: "Среднее",
    1: "Среднее специальное",
    2: "Колледж",
    3: "Высшее",
}

FAMILY_LABELS = {
    0: "Без семьи / не указано",
    1: "В браке, без детей",
    2: "В браке, есть дети",
    3: "Один родитель",
}

HOUSING_LABELS = {
    0: "Своё жильё",
    1: "Аренда",
    2: "Общежитие",
    3: "С родителями",
}

FAMILY_WITH_KIDS = {2, 3}
