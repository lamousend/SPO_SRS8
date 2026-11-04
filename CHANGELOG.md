# Журнал изменений

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), нумерация — семантическая
(`X.Y.Z`: X — несовместимые изменения API, Y — новые возможности, Z — исправления).
Даты выпусков 0.1.0–0.3.0 взяты из истории коммитов репозиториев SPO_PZ7, SPO_PZ8 и SPO_SRS7.

Как выпустить версию:
1. Перенести пункты из раздела «Не выпущено» в новый раздел `## [X.Y.Z] — ГГГГ-ММ-ДД — описание`.
2. `python manage.py generate_api_docs` — версия API в `docs/openapi.json` берётся из этого файла.
3. `python scripts/release_notes.py --check`, затем коммит, `git tag vX.Y.Z` и `git push --tags`.
4. CI проверит, что тег совпадает с последней версией журнала, и создаст GitHub Release с текстом раздела.

## [Не выпущено]

## [0.5.1] — 2026-11-04 — исправления по итогам повторного запуска на Windows
### Исправлено
- `collectstatic` падал на Windows-клоне (`typed.umd.js.map could not be found`): Git заменял переводы строк на CRLF, и `config/storage.py` не распознавал ссылку на `.map`; ссылка теперь обрезается `strip()`.
- `backup_restore.py backup` на Windows падал с `UnicodeDecodeError`: `dumpdata` писал копию в системной кодировке cp1251; дочерние процессы теперь запускаются в режиме UTF-8 (`PYTHONUTF8=1`), копия всегда в UTF-8 и переносится между ОС; убрана полоса прогресса `dumpdata`.
### Добавлено
- `.gitattributes`: `static/` хранится байт-в-байт, `*.sh` — с LF.
- `docs/troubleshooting.md`: ошибки 11 (CRLF и `collectstatic`) и 12 (заглушка Python из Microsoft Store).
- `scripts/make_env.py` — создание `.env` из образца с новым ключом одной командой; основной способ в README и `docs/local-setup.md`.
### Изменено
- `docs/local-setup.md`, `README.md`: создание окружения в Windows при заглушке `python` (`py -3.12 -m venv .venv`), пример строки ключа «было/стало».
- `verify_clean_start.sh` настраивает проект через `make_env.py`, как в инструкции.

## [0.5.0] — 2026-11-04 — СРС № 8: дополнительные возможности
### Добавлено
- `generate_api_docs` создаёт машиночитаемую схему `docs/openapi.json` (OpenAPI 3.0) и таблицы полей, параметров отбора и кодов ответа в `docs/api-reference.md`; описания берутся из `help_text` сериализаторов и docstring-ов ViewSet'ов.
- Контрактные тесты `OpenApiContractTests`: реальные ответы API сверяются со схемой OpenAPI (21 тест вместо 19).
- `backup_restore.py`: команды `verify` (проверка копии на временной пустой базе) и `check` (число записей и согласованность остатков с историей); `restore` отказывается загружать данные в непустую базу без `--force`.
- `verify_clean_start.sh`: копия только файлов репозитория, настройка строго через `cp .env.example .env`, проверка выдачи и остатков после перезапуска, production-режим (DEBUG=false, collectstatic, Gunicorn), режим PostgreSQL (`VERIFY_DATABASE_URL`), итоговая таблица шагов.
- `scripts/release_notes.py` — проверка формата журнала и текст выпуска; CI-задание `release` создаёт GitHub Release по тегу `vX.Y.Z`.
- CI: матрица Python 3.12 / 3.13 и отдельное задание с PostgreSQL 16; `scripts/ci_local.sh` повторяет шаги CI локально.
### Изменено
- Порядок версий журнала приведён к фактической хронологии работ (ПЗ 8 выполнена раньше СРС 7).

## [0.4.0] — 2026-11-04 — СРС № 8: документирование
### Добавлено
- Полный комплект документации: `README.md`, `docs/*.md`.
- `.env.example` для локальной работы; подгрузка `.env` в `config/settings.py` (`load_dotenv`).
- Команда `seed_lab_data` — тестовые категории, оборудование и пользователи.
- Команда `generate_api_docs` — автоматический справочник API (`docs/api-reference.md`).
- Автотесты API `accounts/tests.py` (19 тестов, включая откат транзакции).
- Скрипты `scripts/check_docs.py`, `verify_clean_start.sh`, `smoke_api.py`, `backup_restore.py`.
- CI: `.github/workflows/ci.yml`.
### Исправлено
- `requirements.txt` был в UTF-16 — сохранён в UTF-8 без BOM.
- `README.md` был пустой заглушкой.
- Локальный запуск падал с `ImproperlyConfigured: Set DJANGO_SECRET_KEY`, потому что `.env` нигде не читался.
- `.env.example` содержал значения для Render, непригодные локально.

## [0.3.0] — 2026-11-03 — СРС № 7: бизнес-процесс
### Добавлено
- Модели `Equipment`, `EquipmentReservation`, `ReservationEvent` (миграция 0007).
- Состояния `created → issued → returned`, история событий, транзакции выдачи и возврата, фильтры `status` и `equipment`.
- Страница `/reservations/`.

## [0.2.0] — 2026-10-28 — ПЗ № 8: развёртывание
### Добавлено
- Конфигурация через переменные окружения, `dj-database-url`, WhiteNoise, Gunicorn, `build.sh`, `/healthz/`.
- `config/storage.py` — обход ошибки `collectstatic` на ссылках `.map`.
- Сообщение интерфейса при недоступности API.
### Исправлено
- Дублирующийся блок настроек, перезаписывавший `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASES`.

## [0.1.0] — 2026-10-25 — ПЗ № 7: REST API
### Добавлено
- Модели `Category`, `Ticket`; DRF-сериализаторы с валидацией переходов статуса; страница заявок на Tabler.
