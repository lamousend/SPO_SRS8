# CI и выпуск версий

## Что проверяет CI

Файл .github/workflows/ci.yml запускается в GitHub Actions при каждой загрузке кода.
В CI используются только тестовые значения переменных.

| Задание | Где | Что делает |
|---------|-----|------------|
| docs-and-sqlite | Python 3.12 и 3.13, SQLite | установка зависимостей, check, проверка миграций, 21 автотест, collectstatic, проверка описания API, документации и журнала, резервная копия, запуск с нуля |
| postgres | PostgreSQL 16, как на Render | миграции и автотесты, запуск с нуля, перенос данных из SQLite |
| release | только для тегов вида v0.5.1 | проверка тега и создание выпуска на GitHub |

Что найдет CI:

| Ошибка | Какой шаг упадет |
|--------|------------------|
| маршрут добавлен, а описание не обновлено | generate_api_docs --check и check_docs.py |
| ответы API не совпадают со схемой | контрактные тесты |
| новая переменная не описана в .env.example и deployment.md | check_docs.py |
| неверная ссылка в документации или requirements.txt в UTF-16 | check_docs.py |
| модель изменена без миграции | makemigrations --check |
| ошибка в формате журнала изменений | release_notes.py --check |
| проект не запускается по инструкции | verify_clean_start.sh |
| код работает на SQLite, но не на PostgreSQL | задание postgres |

## Запуск CI на своем компьютере

```bash
python -m pip install pyyaml
python scripts/ci_local.py
python scripts/ci_local.py --postgres postgresql://USER:PASSWORD@localhost:5432
```

Скрипт берет команды прямо из ci.yml и выполняет их в чистой копии проекта.
В конце выводится список шагов.

## Выпуск версии

1. В CHANGELOG.md перенесите пункты из раздела «Не выпущено» в новый раздел ## [X.Y.Z] - дата - описание.
2. python manage.py generate_api_docs - версия API берется из журнала.
3. python scripts/release_notes.py --check и коммит.
4. git tag vX.Y.Z и git push origin vX.Y.Z - CI создаст выпуск на GitHub.
