# Worker Selection App 🚀

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![Build](https://img.shields.io/badge/build-passing-brightgreen)
![ML](https://img.shields.io/badge/ROC--AUC-0.858-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

MVP-система анализа удержания и первичного скрининга линейного персонала. Система объединяет извлечение структурированных данных из резюме (AI) и прогноз стабильности кандидата (ML).

## 🛠 Технологический стек

*   **Backend**: Python 3.11, FastAPI, SQLModel (SQLite)
*   **AI Engine**: Transformers (LLM Qwen), Faster-Whisper (STT)
*   **ML Engine**: CatBoost, Scikit-learn (12 ключевых признаков)
*   **DevOps**: Docker, uv, Makefile, Ruff (Linter/Formatter) 

## 📁 Структура проекта

```text
.
├── app/
│   ├── ai/             # Инференс моделей (STT, LLM, TTS)
│   ├── api/            # Роуты, БД и схемы данных
│   ├── core/           # Конфигурация и энумы
│   ├── ml/             # Генератор данных и предикторы
│   ├── services/       # Сервисный слой (Бизнес-логика)
│   └── ui/             # Демо-API для фронтенда
├── data/               # Датасеты для обучения
├── tests/              # Unit и Integration тесты
├── Dockerfile          # Контейнеризация
├── Makefile            # Автоматизация команд
├── pyproject.toml      # Управление зависимостями (uv)
└── Worker_Selection_App.db
```

## 🚀 Быстрый старт

Проект использует современный менеджер пакетов [uv](https://github.com/astral-sh/uv).

### 1. Установка
```bash
make setup
```

### 2. Запуск сервера
```bash
make run
```
API будет доступно по адресу: `http://127.0.0.1:8000/docs`

### 3. Разработка и проверка качества
```bash
make lint    # Проверка стиля кода (Ruff)
make format  # Авто-форматирование
make test    # Запуск тестов (Pytest)
```

## 🧠 ML-составляющая

Модель обучается на 12 признаках, включая:
*   **Стабильность**: Количество прошлых увольнений.
*   **Логистика**: Время в пути до работы, наличие транспорта.
*   **Профессионализм**: Подтвержденные навыки, сертификаты, опыт.
*   **Социальный профиль**: Возраст, образование, семейный статус.

**Текущий ROC-AUC: 0.858**

## 🐳 Docker

Сборка и запуск в изолированном контейнере:
```bash
make docker-build
docker run -p 8000:8000 worker-selection-app
```

## 📜 Документация
*   [PLAN.md](./PLAN.md) — Дорожная карта проекта.
*   [описание_задачи.md](./описание_задачи.md) — Техническое задание.
