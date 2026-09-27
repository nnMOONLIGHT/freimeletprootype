# Фреймлёт

Творческая платформа для подростков и студентов: портфолио, челленджи, лента видео, маркетплейс и **AI-стилист** на собственной нейросети (Python + NumPy, без OpenAI и сторонних API).

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r backend/requirements.txt
python run.py
```

Откройте [http://127.0.0.1:5000](http://127.0.0.1:5000).

### Демо-аккаунты (после первого запуска)

| Email | Пароль |
|-------|--------|
| demo@freimelet.ru | demo123 |
| eva@freimelet.ru | demo123 |

## Что внутри

- **Регистрация** вместо Госуслуг: роль, ФИО, возраст, регион, согласие родителя (шаблон для скачивания).
- **SQLite** — пользователи, работы, активность, история AI-анализов, лента видео.
- **Нейросеть** — `backend/neural/`: извлечение признаков из фото (PIL + NumPy), MLP с backprop, подбор стиля, увлечений, одежды и палитры.
- **Адаптив** — десктоп (сайдбар) и мобильная нижняя навигация.

## Структура

```
backend/          Flask API, БД, neural/
frontend/         HTML, CSS, JS, static/img/logo.png
run.py            Точка входа
data/             SQLite (создаётся автоматически)
```

## Деплой

GitHub Pages отдаёт только статику; для регистрации, БД и AI нужен Python-хостинг (Render, Railway, VPS):

1. `pip install -r backend/requirements.txt`
2. `gunicorn -w 2 -b 0.0.0.0:$PORT "backend.app:app"` (из корня, с `PYTHONPATH=backend`)
3. Переменная `FREIMELET_SECRET` — секрет сессий.

Логотип: `frontend/static/img/logo.png`.

## Лицензия

Проект для конкурса / портфолио. Домен и репозиторий — на усмотрение команды.
