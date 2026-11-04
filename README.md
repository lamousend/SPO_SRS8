# SPO_SRS8 — учебная система: заявки и бронирование оборудования

Django-проект с интерфейсом на Tabler и REST API на Django REST Framework.
Объединяет результаты ПЗ № 7 (заявки), СРС № 7 (бронирование оборудования
с историей и транзакциями) и ПЗ № 8 (подготовка к эксплуатации и публикация
на Render). Репозиторий передаётся другому разработчику вместе с полным
комплектом документации: после прочтения этого файла проект можно
установить и запустить без устных пояснений автора.

## Назначение

Система решает две учебные задачи для зарегистрированных пользователей:

1. Заявки — создание заявки в выбранной категории и последовательная
   смена статуса `Новая → В работе → Выполнена`.
2. Бронирование оборудования — создание бронирования ограниченного
   ресурса, его выдача и возврат с контролем остатка и журналом событий.

Предназначена для студентов и преподавателей как пример полного цикла
«интерфейс → REST API → база данных → публикация».

## Функциональность

| Сценарий | Что умеет пользователь | Ограничения |
|----------|------------------------|-------------|
| Заявки (`/`) | Создать, изменить статус, удалить, фильтровать по статусу | Видит только свои заявки; статус меняется строго по цепочке, пропуск или откат — HTTP 400 |
| Бронирования (`/reservations/`) | Создать, редактировать, удалить, выдать, вернуть, смотреть историю, фильтровать по статусу и оборудованию | Редактировать и удалять можно только состояние `created`; выдача требует достаточного остатка; удаление «мягкое», история сохраняется |
| Справочники (`/departments/`, `/groups/`, `/courses/`) | Просмотр; изменение — роль «Методист» | Группа `Методист` задаётся в админ-панели |
| Администрирование (`/admin/`) | Добавление категорий и оборудования, управление пользователями | Только суперпользователь / персонал |
| Проверка работоспособности (`/healthz/`) | Возвращает `{"status": "ok"}` без обращения к БД | — |

Оборудование и категории заявок через REST API доступны только для чтения:
добавляются через `/admin/` или командой `seed_lab_data`.

## Технологии

| Компонент | Версия / назначение |
|-----------|---------------------|
| Python | 3.12 или новее |
| Django | 6.1.1 |
| Django REST Framework | 3.18.3, сессионная аутентификация |
| Tabler + JavaScript (`fetch`) | интерфейс, лежит в `static/core/`, подключается локально |
| SQLite | локальная БД по умолчанию (`db.sqlite3`) |
| PostgreSQL + psycopg 3 | облачная БД (Render) |
| dj-database-url | выбор БД по переменной `DATABASE_URL` |
| Gunicorn | WSGI-сервер в эксплуатации |
| WhiteNoise | раздача статических файлов |

Точные версии всех пакетов закреплены в [requirements.txt](requirements.txt).

## Структура документации

| Файл | Содержание |
|------|------------|
| [docs/project-structure.md](docs/project-structure.md) | каталоги и конфигурационные файлы |
| [docs/architecture.md](docs/architecture.md) | архитектурная схема и границы взаимодействия |
| [docs/database.md](docs/database.md) | модели БД, поля, связи, миграции |
| [docs/api.md](docs/api.md) | карточки всех REST-маршрутов с примерами |
| [docs/api-reference.md](docs/api-reference.md) | справочник маршрутов, параметров и полей, создаётся автоматически |
| [docs/openapi.json](docs/openapi.json) | схема OpenAPI 3.0, создаётся автоматически (Swagger Editor, Postman) |
| [docs/ci-and-releases.md](docs/ci-and-releases.md) | CI, локальный прогон CI, выпуск версий |
| [docs/local-setup.md](docs/local-setup.md) | запуск с нуля на своём компьютере |
| [docs/deployment.md](docs/deployment.md) | развёртывание на Render + PostgreSQL |
| [docs/troubleshooting.md](docs/troubleshooting.md) | типичные ошибки и диагностика |
| [docs/reproducibility.md](docs/reproducibility.md) | протокол проверки чистого запуска |
| [docs/backup-restore.md](docs/backup-restore.md) | резервная копия и восстановление данных |
| [CHANGELOG.md](CHANGELOG.md) | журнал изменений релизов |

## Подготовка

Нужны Python 3.12+ и Git. Проверка: `python --version` (в Windows также
может называться `py --version`). Если в Windows `python` выводит только слово `Python`, это заглушка
Microsoft Store: создайте окружение командой `py -3.12 -m venv .venv` (подробнее — [docs/local-setup.md](docs/local-setup.md)).

```bash
git clone https://github.com/lamousend/SPO_SRS8.git
cd SPO_SRS8
python -m venv .venv
```

Активация окружения:

| ОС | Команда |
|----|---------|
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Linux / macOS | `source .venv/bin/activate` |

```bash
python -m pip install -r requirements.txt
```

## Настройка

Секреты и режимы работы берутся из переменных окружения. Для локальной
работы создайте файл `.env` из образца с новым случайным ключом (файл читается
автоматически и не попадает в Git):

```bash
python scripts/make_env.py
```

Вручную: `cp .env.example .env` (Windows: `copy`) и замена значения после `=` в строке
`DJANGO_SECRET_KEY=` — см. [docs/local-setup.md](docs/local-setup.md).

| Переменная | Назначение | Локальное значение-пример |
|------------|------------|---------------------------|
| `DJANGO_SECRET_KEY` | секретный ключ Django, обязательна | `replace-with-a-long-random-string` (замените своим) |
| `DJANGO_DEBUG` | режим отладки; в облаке всегда `false` | `true` |
| `DJANGO_ALLOWED_HOSTS` | разрешённые домены через запятую | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | доверенные HTTPS-источники для CSRF | пусто |
| `DATABASE_URL` | адрес БД; не задана — SQLite | не задавать |

Подробности и безопасные способы генерации ключа — в
[docs/deployment.md](docs/deployment.md).

## Запуск

```bash
python manage.py migrate
python manage.py seed_lab_data --password "ВашПароль123"
python manage.py createsuperuser
python manage.py runserver
```

`seed_lab_data` создаёт 3 категории, 3 вида оборудования и пользователей
`student1`, `student2` с указанным паролем (команда повторяемая — дубликатов
не будет). Адреса страниц:

| Адрес | Что открывается |
|-------|-----------------|
| http://127.0.0.1:8000/accounts/login/ | вход |
| http://127.0.0.1:8000/ | заявки |
| http://127.0.0.1:8000/reservations/ | бронирование оборудования |
| http://127.0.0.1:8000/admin/ | административная панель |
| http://127.0.0.1:8000/healthz/ | проверка работоспособности |

## Проверка

1. UI: войти как `student1`, создать бронирование на странице
   `/reservations/` — появляется сообщение об успехе, список обновляется
   без перезагрузки.
2. API: в DevTools → Network виден `POST /api/reservations/` со статусом
   `201`; `GET /api/reservations/` возвращает созданную запись.
3. БД: после перезапуска сервера и обновления страницы запись остаётся;
   либо `python manage.py shell -c "from accounts.models import EquipmentReservation as R; print(R.objects.count())"`.
4. Автоматически: `python manage.py test accounts` (21 тест) или
   полный сценарий `bash scripts/verify_clean_start.sh`.

## Развёртывание

Публикация на Render (Web Service + PostgreSQL), переменные окружения,
миграции, статика и проверка — [docs/deployment.md](docs/deployment.md).
Локальная SQLite и облачная PostgreSQL — разные базы, данные между
ними не переносятся автоматически (см. [docs/backup-restore.md](docs/backup-restore.md)).

## Дополнительные инструменты (повышенный уровень)

| Возможность | Как использовать | Подробнее |
|-------------|------------------|-----------|
| Автогенерация описания API (справочник + OpenAPI 3.0, контрактные тесты) | `python manage.py generate_api_docs` | [api-reference.md](docs/api-reference.md) |
| Проверка документации в CI (SQLite, Python 3.12/3.13, PostgreSQL 16) | `.github/workflows/ci.yml`; локально `python scripts/ci_local.py` | [ci-and-releases.md](docs/ci-and-releases.md) |
| Сценарий восстановления данных | `python scripts/backup_restore.py backup / verify / restore / check` | [backup-restore.md](docs/backup-restore.md) |
| Автоматическая проверка чистого запуска | `bash scripts/verify_clean_start.sh` | [reproducibility.md](docs/reproducibility.md) |
| Журнал изменений релизов | [CHANGELOG.md](CHANGELOG.md), `python scripts/release_notes.py --check` | [ci-and-releases.md](docs/ci-and-releases.md) |
