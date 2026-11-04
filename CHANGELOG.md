# Журнал изменений


## [0.5.0] - 2026-11-04 - СРС № 8: дополнительные возможности
### Добавлено
- generate_api_docs создает схему OpenAPI (docs/openapi.json) и таблицы полей в docs/api-reference.md.
- Контрактные тесты: ответы API сверяются со схемой OpenAPI (21 тест).
- backup_restore.py: команды verify и check, restore не загружает данные в непустую базу.
- verify_clean_start.sh: чистая копия репозитория, проверка после перезапуска, production-режим, PostgreSQL.
- release_notes.py: проверка журнала и текст выпуска; выпуск на GitHub по тегу.
- CI: Python 3.12 и 3.13, отдельное задание на PostgreSQL 16; ci_local.py для запуска CI локально.

## [0.4.0] - 2026-11-04 - СРС № 8: документация
### Добавлено
- README.md и папка docs/ с полной документацией.
- .env.example для локальной работы; settings.py читает файл .env.
- Команда seed_lab_data - тестовые данные.
- Команда generate_api_docs - справочник API.
- Автотесты API (19 тестов).
- Скрипты check_docs.py, verify_clean_start.sh, smoke_api.py, backup_restore.py и CI.
### Исправлено
- requirements.txt пересохранен из UTF-16 в UTF-8.
- Пустой README.md.
- Ошибка ImproperlyConfigured: Set DJANGO_SECRET_KEY при локальном запуске.
- .env.example подходил только для Render.

## [0.3.0] - 2026-11-03 - СРС № 7: бронирование оборудования
### Добавлено
- Модели Equipment, EquipmentReservation, ReservationEvent (миграция 0007).
- Состояния created, issued, returned, история событий, транзакции выдачи и возврата, фильтры status и equipment.
- Страница /reservations/.

## [0.2.0] - 2026-10-28 - ПЗ № 8: публикация
### Добавлено
- Настройки через переменные окружения, dj-database-url, WhiteNoise, Gunicorn, build.sh, /healthz/.
- config/storage.py - обход ошибки collectstatic на ссылках .map.
- Сообщение на странице, если API недоступен.
### Исправлено
- Повторяющийся блок настроек, который перезаписывал SECRET_KEY, ALLOWED_HOSTS и DATABASES.

## [0.1.0] - 2026-10-25 - ПЗ № 7: REST API
### Добавлено
- Модели Category и Ticket, проверка смены статуса, страница заявок на Tabler.
