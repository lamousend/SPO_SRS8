# CI, локальный прогон и выпуск версий

## Что проверяет CI

Workflow `.github/workflows/ci.yml` запускается на каждый `push` и `pull_request` в GitHub Actions.
В CI используются только фиктивные значения переменных (`ci-only-...`), реальных секретов в репозитории нет.

| Задание | Окружение | Шаги |
|---------|-----------|------|
| `docs-and-sqlite` | Python 3.12 и 3.13 (матрица), SQLite | `pip install -r requirements.txt`; `check`; `makemigrations --check`; 21 автотест (включая контрактные тесты OpenAPI); `collectstatic`; `generate_api_docs --check`; `check_docs.py`; `release_notes.py --check`; копия данных + `verify`; `verify_clean_start.sh` |
| `postgres` | PostgreSQL 16 (сервис-контейнер, как на Render) | миграции и автотесты на PostgreSQL; `verify_clean_start.sh` на пустой PostgreSQL; перенос данных SQLite → PostgreSQL через `backup_restore.py` |
| `release` | только для тегов `v*`, после успеха двух заданий | тег совпадает с последней версией `CHANGELOG.md`; GitHub Release с текстом раздела журнала |

Что ловит CI:

| Ошибка разработчика | Шаг, который упадёт |
|---------------------|---------------------|
| добавлен маршрут API, а описание не обновлено | `generate_api_docs --check`, `check_docs.py` (маршрут без карточки в `api.md`) |
| схема `openapi.json` расходится с ответами API | контрактные тесты `OpenApiContractTests` |
| в `settings.py` появилась переменная, не описанная в `.env.example` и `deployment.md` | `check_docs.py` |
| битая ссылка в Markdown, `requirements.txt` в UTF-16 или без версий | `check_docs.py` |
| изменена модель без миграции | `makemigrations --check` |
| запись журнала не по формату, версии не по убыванию | `release_notes.py --check` |
| проект не запускается из чистой копии по инструкции | `verify_clean_start.sh` |
| код работает на SQLite, но не на PostgreSQL | задание `postgres` |

## Локальный прогон CI

```bash
python -m pip install pyyaml                     # нужен только для ci_local.py
python scripts/ci_local.py                       # задание docs-and-sqlite
python scripts/ci_local.py --postgres postgresql://USER:PASSWORD@localhost:5432
                                                 # + задание postgres (пользователь с правом CREATE DATABASE)
python scripts/ci_local.py --install             # выполнить и шаг pip install
```

Скрипт читает сам `ci.yml`, поэтому выполняет ровно те же команды, что GitHub Actions, в чистой копии репозитория
с переменными окружения из workflow; шаги `uses:` заменяются копированием и текущим Python. Базы `app`, `verify`,
`restored` пересоздаются. В конце печатается таблица шагов, код возврата 0 — всё пройдено.

## Выпуск версии

1. В `CHANGELOG.md` перенести пункты из «Не выпущено» в раздел `## [X.Y.Z] — ГГГГ-ММ-ДД — описание`
   (разделы: Добавлено, Изменено, Исправлено, Удалено, Безопасность).
2. `python manage.py generate_api_docs` — версия API в `docs/openapi.json` берётся из журнала.
3. `python scripts/release_notes.py --check` и коммит.
4. `git tag vX.Y.Z && git push origin vX.Y.Z` — задание `release` проверит тег и создаст GitHub Release.

`python scripts/release_notes.py X.Y.Z` печатает текст раздела версии (его же CI использует как описание выпуска).
