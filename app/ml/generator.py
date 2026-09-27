"""
Synthetic Data Generator (Rule-Based)
ТЗ: Скрипт генерации train.csv (1000 строк) с жесткими правилами
Пример правила: Если Commute > 90 мин, то Retention = 0
"""

import math
import os
import random

import pandas as pd

from app.core.enums import ShiftPreference
from app.ml.feature_contract import FEATURE_COLS

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
DEFAULT_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "train_dataset.csv")


class SyntheticDataGenerator:
    def __init__(self, n_samples=1000):
        self.n_samples = n_samples
        self.rng = random.Random()

    def _generate_age_and_experience(self) -> tuple[int, float]:
        age = self.rng.randint(20, 60)

        career_start_age = self.rng.choices(
            population=[18, 19, 20, 21, 22, 23, 24],
            weights=[1, 3, 5, 5, 4, 2, 1],
            k=1,
        )[0]

        career_start_age = min(career_start_age, age)
        max_experience = max(0, age - career_start_age)

        years_experience = round(
            self.rng.triangular(0, max_experience, max_experience * 0.6),
            1,
        )

        return age, years_experience

    def _compute_risk_score(
        self,
        skills_verified_count: int,
        years_experience: float,
        age: int,
        commute_time_minutes: int,
        shift_preference: ShiftPreference,
        salary_expectation: int,
        has_certifications: bool,
        education_level: int,
        previous_turnovers: int,
        family_status: int,
        housing_type: int,
        has_transport: bool,
    ) -> float:
        score = 0.0

        # Время в пути
        if commute_time_minutes > 120:
            score += 2.6
        elif commute_time_minutes > 90:
            score += 1.8
        elif commute_time_minutes > 60:
            score += 0.8
        else:
            score -= 0.2

        # Навыки
        if skills_verified_count < 3:
            score += 2.2
        elif skills_verified_count < 5:
            score += 0.9
        elif skills_verified_count >= 8:
            score -= 0.5

        # Опыт
        if years_experience < 1:
            score += 1.8
        elif years_experience < 3:
            score += 0.9
        elif years_experience >= 8:
            score -= 0.5

        # Сменность и возраст
        if shift_preference == ShiftPreference.NIGHT_ONLY:
            score += 0.5
            if age > 50:
                score += 1.0
        elif shift_preference == ShiftPreference.ANY:
            score += 0.1

        # Зарплатные ожидания относительно опыта
        if years_experience < 2 and salary_expectation > 100000:
            score += 1.7
        elif years_experience < 4 and salary_expectation > 120000:
            score += 0.9

        # Сертификаты
        if not has_certifications:
            score += 0.4
            if skills_verified_count > 5:
                score += 0.8
        else:
            score -= 0.2

        # Взаимодействия признаков
        if commute_time_minutes > 90 and shift_preference == ShiftPreference.NIGHT_ONLY:
            score += 0.4

        if skills_verified_count < 3 and years_experience < 2:
            score += 0.6

        # Частые увольнения / смены работы
        if previous_turnovers > 3:
            score += 2.4
        elif previous_turnovers >= 2:
            score += 1.0
        elif previous_turnovers == 0:
            score -= 0.3

        # Семья + ночные смены
        has_kids = family_status in {2, 3}

        if has_kids and shift_preference == ShiftPreference.NIGHT_ONLY:
            score += 1.3

        # Транспорт и дорога
        if not has_transport and commute_time_minutes > 60:
            score += 1.0
        elif has_transport and commute_time_minutes <= 60:
            score -= 0.3

        # Жильё
        if housing_type == 2:
            score += 0.6
        elif housing_type == 0:
            score -= 0.3

        # Образование
        if education_level in {1, 2}:
            score -= 0.4
        elif education_level == 0 and skills_verified_count < 3:
            score += 0.4

        # Небольшой джиттер вместо грубого flip 5%
        score += self.rng.uniform(-0.25, 0.25)

        return score

    def generate_dataset(self):
        """Генерация датасета с жесткими правилами для удержания"""
        data = []

        while len(data) < self.n_samples:
            # Генерация признаков для ML модели
            skills_verified_count = self.rng.randint(0, 10)
            age, years_experience = self._generate_age_and_experience()
            commute_time_minutes = self.rng.randint(10, 180)
            shift_preference = self.rng.choice(list(ShiftPreference))
            salary_expectation = self.rng.randint(30000, 150000)
            has_certifications = self.rng.random() > 0.7

            education_level = self.rng.choices(
                population=[0, 1, 2, 3],
                weights=[20, 40, 25, 15],
                k=1,
            )[0]

            previous_turnovers = self.rng.choices(
                population=[0, 1, 2, 3, 4, 5],
                weights=[25, 30, 20, 12, 8, 5],
                k=1,
            )[0]

            family_status = self.rng.choices(
                population=[0, 1, 2, 3],
                weights=[35, 25, 30, 10],
                k=1,
            )[0]

            housing_type = self.rng.choices(
                population=[0, 1, 2, 3],
                weights=[25, 45, 15, 15],
                k=1,
            )[0]

            has_transport = self.rng.random() > 0.45

            risk_score = self._compute_risk_score(
                skills_verified_count=skills_verified_count,
                years_experience=years_experience,
                age=age,
                commute_time_minutes=commute_time_minutes,
                shift_preference=shift_preference,
                salary_expectation=salary_expectation,
                has_certifications=has_certifications,
                education_level=education_level,
                previous_turnovers=previous_turnovers,
                family_status=family_status,
                housing_type=housing_type,
                has_transport=has_transport,
            )

            # Чем выше risk_score, тем ниже вероятность удержания
            retention_probability = 1.0 / (1.0 + math.exp(risk_score - 2.0))
            retention = 1 if self.rng.random() < retention_probability else 0

            record = {
                "skills_verified_count": skills_verified_count,
                "years_experience": round(years_experience, 1),
                "age": age,
                "commute_time_minutes": commute_time_minutes,
                "shift_preference": shift_preference.value,
                "salary_expectation": salary_expectation,
                "has_certifications": int(has_certifications),
                "education_level": education_level,
                "previous_turnovers": previous_turnovers,
                "family_status": family_status,
                "housing_type": housing_type,
                "has_transport": int(has_transport),
                "retention": retention,
            }

            max_allowed_experience = max(0, age - 18)
            if years_experience > max_allowed_experience:
                continue

            data.append(record)

        return pd.DataFrame(data)

    def save_to_csv(self, path=DEFAULT_DATA_PATH):
        """Сохранение в CSV файл"""
        import os

        os.makedirs(os.path.dirname(path), exist_ok=True)

        df = self.generate_dataset()
        df.to_csv(path, index=False)
        print(f"Данные сохранены в {path}")
        return df


def generate_if_needed():
    """Проверяет наличие датасета и генерирует если нужно"""
    data_path = DEFAULT_DATA_PATH
    should_generate = False

    if not os.path.exists(data_path) or os.path.getsize(data_path) == 0:
        should_generate = True
    else:
        try:
            df = pd.read_csv(data_path)

            required_columns = set(FEATURE_COLS + ["retention"])
            missing_columns = required_columns - set(df.columns)

            if missing_columns:
                print(f"В датасете нет колонок {sorted(missing_columns)}. Перегенерация...")
                should_generate = True
            else:
                invalid_rows = df[df["years_experience"] > (df["age"] - 18).clip(lower=0)]

                if not invalid_rows.empty:
                    print(f"Найдено {len(invalid_rows)} нереалистичных строк. Перегенерация...")
                    should_generate = True
        except Exception:
            should_generate = True

    if should_generate:
        print("Генерация тренировочных данных...")
        generator = SyntheticDataGenerator(n_samples=1000)
        df = generator.save_to_csv(data_path)
        print(f"Сгенерировано {len(df)} записей в {data_path}")
    else:
        print(f"Датасет уже существует и корректен: {data_path}")

    return data_path
