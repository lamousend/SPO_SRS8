# Структура проекта

Дерево основных каталогов (кэш `__pycache__`, `static/core/`, `.idea/` не показаны):

```text
SPO_SRS8/
├── manage.py                    # точка входа Django-команд
├── requirements.txt             # закреплённые зависимости (UTF-8)
├── build.sh                     # команды сборки для Render
├── .env.example                 # образец переменных окружения (без секретов)
├── .gitignore                   # исключает .env, db.sqlite3, staticfiles/, backups/
├── README.md, CHANGELOG.md
├── .github/workflows/ci.yml     # проверки в CI
├── config/                      # проект Django
│   ├── settings.py              # настройки; секреты берёт из окружения
│   ├── urls.py                  # корневые маршруты, /healthz/
│   ├── storage.py               # хранилище статики для WhiteNoise
│   ├── wsgi.py / asgi.py        # точки входа серверов приложений
├── accounts/                    # основное приложение
│   ├── models.py                # все модели предметной области
│   ├── serializers.py           # DRF: Category, Ticket
│   ├── res_serializers.py       # DRF: Equipment, EquipmentReservation, ReservationEvent
│   ├── reservation_services.py  # транзакции выдачи и возврата
│   ├── views.py                 # страницы и ViewSet'ы API
│   ├── urls.py                  # страницы + DefaultRouter (/api/...)
│   ├── admin.py, forms.py
│   ├── tests.py                 # автотесты API и контрактные тесты OpenAPI (21)
│   ├── migrations/              # 0001–0007
│   ├── templates/tickets/       # страница заявок
│   ├── templates/reservations/  # страница бронирований
│   ├── static/tickets/app.js    # fetch-клиент заявок
│   ├── static/reservations/app.js
│   └── management/commands/     # seed_lab_data, generate_api_docs
├── dashboards/                  # дашборды и журнал активности (ActivityEvent)
├── templates/                   # общие шаблоны: base.html, login, формы
├── static/                      # Tabler (core/), css/, js/, vendor/
├── scripts/                     # check_docs.py, verify_clean_start.sh, smoke_api.py,
│                                # backup_restore.py, release_notes.py, ci_local.py, make_env.py
└── docs/                        # документация; api-reference.md и openapi.json создаются автоматически
```

## Назначение основных каталогов

| Путь | Назначение |
|------|------------|
| `config/` | настройки проекта, маршруты верхнего уровня, WSGI |
| `accounts/` | заявки, бронирование, справочники учебной части, REST API |
| `dashboards/` | страницы-дашборды и журнал событий (создаётся сигналами) |
| `templates/` | базовый шаблон Tabler, страницы входа и ошибок |
| `static/` | исходные статические файлы; `collectstatic` собирает их в `staticfiles/` |
| `staticfiles/` | **создаётся сборкой**, в Git не хранится; из него WhiteNoise отдаёт файлы |
| `scripts/` | сценарии проверки документации, чистого запуска, копирования данных, выпуска версий и локального CI |
| `docs/` | вся техническая документация |

## Конфигурационные файлы

| Файл | Для чего | Секреты? |
|------|----------|----------|
| `config/settings.py` | настройки Django, чтение переменных окружения | нет, только имена переменных |
| `.env.example` | образец; копируется в `.env` | нет |
| `.env` | локальные значения | **да**, в Git не попадает |
| `requirements.txt` | зависимости для `pip install -r` | нет |
| `build.sh` | `pip install` + `collectstatic` при сборке на Render | нет |
| `.gitignore` | исключения Git | нет |
| `.github/workflows/ci.yml` | автопроверки при `push` | нет (в CI фиктивные значения) |
| `db.sqlite3` | локальная БД (создаётся `migrate`) | данные пользователей; в Git не попадает |
