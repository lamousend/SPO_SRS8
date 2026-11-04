# SPO_SRS8 - заявки и бронирование оборудования

Учебный Django-проект: интерфейс на Tabler и REST API на Django REST Framework.
Объединяет ПЗ № 7 (заявки), СРС № 7 (бронирование оборудования) и ПЗ № 8 (публикация на Render).
По этому файлу проект можно установить и запустить без помощи автора.

## Назначение

Система решает две задачи для зарегистрированных пользователей:

1. Заявки - создание заявки и смена статуса по цепочке: Новая - В работе - Выполнена.
2. Бронирование оборудования - бронирование, выдача и возврат с учетом остатка и историей событий.

## Функциональность

| Раздел | Что можно сделать | Ограничения |
|--------|-------------------|-------------|
| Заявки (/) | создать, сменить статус, удалить, отфильтровать | видны только свои заявки; статус нельзя пропустить или вернуть назад (ошибка 400) |
| Бронирования (/reservations/) | создать, изменить, удалить, выдать, вернуть, посмотреть историю, отфильтровать | менять и удалять можно только созданное бронирование; для выдачи нужен остаток; при удалении история сохраняется |
| Справочники (/departments/, /groups/, /courses/) | просмотр; изменение - для группы «Методист» | группа задается в админ-панели |
| Админ-панель (/admin/) | категории, оборудование, пользователи | только для администратора |
| Проверка сервера (/healthz/) | ответ {"status": "ok"} | - |

Категории и оборудование через API только читаются. Добавить их можно в /admin/ или командой seed_lab_data.

## Технологии

| Компонент | Версия и назначение |
|-----------|---------------------|
| Python | 3.12 или новее |
| Django | 6.1.1 |
| Django REST Framework | 3.18.3, вход по сессии |
| Tabler и JavaScript (fetch) | интерфейс, файлы в static/core/ |
| SQLite | база для локального запуска |
| PostgreSQL и psycopg 3 | база на Render |
| dj-database-url | выбор базы по DATABASE_URL |
| Gunicorn | сервер на Render |
| WhiteNoise | выдача статических файлов |

Точные версии пакетов - в [requirements.txt](requirements.txt).

## Структура документации

| Файл | Что внутри |
|------|------------|
| [docs/project-structure.md](docs/project-structure.md) | каталоги и файлы настроек |
| [docs/architecture.md](docs/architecture.md) | схема и путь запроса |
| [docs/database.md](docs/database.md) | модели, поля, связи, миграции |
| [docs/api.md](docs/api.md) | описание всех маршрутов API |
| [docs/api-reference.md](docs/api-reference.md) | справочник API, создается автоматически |
| [docs/openapi.json](docs/openapi.json) | схема OpenAPI 3.0, создается автоматически |
| [docs/local-setup.md](docs/local-setup.md) | запуск на своем компьютере |
| [docs/deployment.md](docs/deployment.md) | публикация на Render |
| [docs/troubleshooting.md](docs/troubleshooting.md) | типичные ошибки |
| [docs/reproducibility.md](docs/reproducibility.md) | проверка запуска с нуля |
| [docs/backup-restore.md](docs/backup-restore.md) | резервная копия данных |
| [docs/ci-and-releases.md](docs/ci-and-releases.md) | CI и выпуск версий |
| [CHANGELOG.md](CHANGELOG.md) | журнал изменений |

## Подготовка

Нужны Python 3.12+ и Git.

```bash
git clone https://github.com/lamousend/SPO_SRS8.git
cd SPO_SRS8
python -m venv .venv
```

Если в Windows команда python выводит только слово Python, используйте py -3.12 -m venv .venv
(подробнее - в [docs/local-setup.md](docs/local-setup.md)).

Активация окружения:

| Система | Команда |
|---------|---------|
| Windows PowerShell | .venv\Scripts\Activate.ps1 |
| Linux, macOS | source .venv/bin/activate |

```bash
python -m pip install -r requirements.txt
```

## Настройка

Настройки берутся из переменных окружения. Для локального запуска создайте файл .env с новым ключом:

```bash
python scripts/make_env.py
```

Файл .env читается автоматически и не попадает в Git.

| Переменная | Назначение | Значение для локального запуска |
|------------|------------|---------------------------------|
| DJANGO_SECRET_KEY | секретный ключ, обязателен | создается командой make_env.py |
| DJANGO_DEBUG | режим отладки; в облаке всегда false | true |
| DJANGO_ALLOWED_HOSTS | разрешенные адреса через запятую | localhost,127.0.0.1 |
| DJANGO_CSRF_TRUSTED_ORIGINS | разрешенные HTTPS-адреса для форм | пусто |
| DATABASE_URL | адрес базы; если не задан - SQLite | не задавать |

Значения для Render - в [docs/deployment.md](docs/deployment.md).

## Запуск

```bash
python manage.py migrate
python manage.py seed_lab_data --password "ВашПароль123"
python manage.py createsuperuser
python manage.py runserver
```

seed_lab_data создает 3 категории, 3 вида оборудования и пользователей student1 и student2.
Повторный запуск дубликатов не создает.

| Адрес | Страница |
|-------|----------|
| http://127.0.0.1:8000/accounts/login/ | вход |
| http://127.0.0.1:8000/ | заявки |
| http://127.0.0.1:8000/reservations/ | бронирование оборудования |
| http://127.0.0.1:8000/admin/ | админ-панель |
| http://127.0.0.1:8000/healthz/ | проверка сервера |

## Проверка

1. Интерфейс: войдите как student1 и создайте бронирование - появится сообщение об успехе.
2. API: в браузере на вкладке Network виден POST /api/reservations/ с кодом 201.
3. База: после перезапуска сервера бронирование остается на месте.
4. Автотесты: python manage.py test accounts (21 тест) или bash scripts/verify_clean_start.sh.

## Развертывание

Публикация на Render (Web Service и PostgreSQL) - в [docs/deployment.md](docs/deployment.md).
Локальная SQLite и PostgreSQL на Render - разные базы, данные между ними сами не переносятся
(см. [docs/backup-restore.md](docs/backup-restore.md)).

## Дополнительные инструменты

| Инструмент | Команда | Подробнее |
|------------|---------|-----------|
| Описание API из кода | python manage.py generate_api_docs | [api-reference.md](docs/api-reference.md) |
| Проверка документации в CI | python scripts/check_docs.py, локально python scripts/ci_local.py | [ci-and-releases.md](docs/ci-and-releases.md) |
| Резервная копия и восстановление | python scripts/backup_restore.py backup / verify / restore / check | [backup-restore.md](docs/backup-restore.md) |
| Проверка запуска с нуля | bash scripts/verify_clean_start.sh | [reproducibility.md](docs/reproducibility.md) |
| Журнал изменений | python scripts/release_notes.py --check | [CHANGELOG.md](CHANGELOG.md) |
