# Локальный запуск с нуля

Инструкция проверена на чистом каталоге и пустой базе. Команды даны для Windows PowerShell
и Linux/macOS; отличающиеся строки помечены.

## 1. Требования

| Что | Версия | Проверка |
|-----|--------|----------|
| Python | 3.12+ | `python --version` |
| Git | любая | `git --version` |
| Интернет | для `pip install` | — |

PostgreSQL локально **не нужен**: без `DATABASE_URL` используется SQLite.

## 2. Получение кода и окружение

```bash
git clone https://github.com/lamousend/SPO_SRS8.git
cd SPO_SRS8
python -m venv .venv
```

Windows: если `python -m venv .venv` выводит только слово `Python` и папка `.venv` не появляется,
`python` указывает на заглушку Microsoft Store (проверка: `where.exe python` — первым идёт `...\WindowsApps\python.exe`).
Создайте окружение через лаунчер или полный путь к установленному Python, после активации `python` уже работает:

```powershell
py -3.12 -m venv .venv
# или: & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv
```

| ОС | Активация |
|----|-----------|
| Windows PowerShell | `.venv\Scripts\Activate.ps1` (если запрещено выполнение скриптов: `Set-ExecutionPolicy -Scope Process RemoteSigned`) |
| Linux / macOS | `source .venv/bin/activate` |

Признак успеха — префикс `(.venv)` в приглашении и `python --version` → `Python 3.12…`
(не просто `Python`). В каждом новом окне терминала окружение активируется заново.

## 3. Зависимости

```bash
python -m pip install -r requirements.txt
```

Проверка: `python -m pip list` содержит `Django 6.1.1`, `djangorestframework 3.18.3`,
`whitenoise 6.12.0`, `gunicorn 26.2.0`.

## 4. Конфигурация

```bash
python scripts/make_env.py
```

Скрипт копирует `.env.example` в `.env` и записывает в него новый случайный ключ (на экран ключ не выводится).
Ожидается: `Создан .env: ключ DJANGO_SECRET_KEY записан …` и список переменных, в котором есть
`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`. Пересоздать файл: `python scripts/make_env.py --force`.

Вручную: `cp .env.example .env` (Windows: `copy .env.example .env`), ключ —
`python -c "import secrets; print(secrets.token_urlsafe(50))"`. Заменяется только часть после знака `=`,
имя переменной остаётся:

```text
было:   DJANGO_SECRET_KEY=replace-with-a-long-random-string
стало:  DJANGO_SECRET_KEY=Xq3...ваш_ключ...9Zk
```

Если вместо строки целиком вставить один ключ, Django его не найдёт и сообщит `ImproperlyConfigured: Set DJANGO_SECRET_KEY`.

Остальные значения для локальной работы менять не нужно (`DJANGO_DEBUG=true`,
`DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`, `DATABASE_URL` не задан).
Файл `.env` читается автоматически при каждом запуске `manage.py`; уже заданные в системе
переменные имеют приоритет. Без ключа проект не стартует (`ImproperlyConfigured: Set DJANGO_SECRET_KEY`).

Проверка конфигурации:

```bash
python manage.py check
```

Ожидается: `System check identified no issues (0 silenced).`

## 5. Миграции

```bash
python manage.py migrate
```

Ожидается список `Applying accounts.0001_initial... OK` … `Applying accounts.0007_equipment_equipmentreservation_reservationevent... OK`,
`dashboards.0001_initial`, `sessions.0001_initial`. Состояние: `python manage.py showmigrations` — все пункты отмечены `[X]`.

## 6. Тестовые данные

```bash
python manage.py seed_lab_data --password "ВашПароль123"
python manage.py createsuperuser
```

Создаются категории «Оборудование», «Программное обеспечение», «Сетевые сервисы»;
оборудование «Проектор» (2), «Ноутбук» (5), «Графический планшет» (3); пользователи `student1`, `student2`.
Повторный запуск дубликатов не создаёт. Суперпользователь нужен для `/admin/`.

Необязательно: `python manage.py seed_demo_data` — демо-студенты и журнал для страниц-дашбордов.

## 7. Запуск

```bash
python manage.py runserver
```

Откройте <http://127.0.0.1:8000/accounts/login/> и войдите как `student1`.

## 8. Проверка

| Что | Как | Ожидание |
|-----|-----|----------|
| Сервис жив | `curl http://127.0.0.1:8000/healthz/` | `{"status": "ok"}` |
| UI | страница `/reservations/` | форма, таблица остатков и список в стиле Tabler |
| API (GET) | DevTools → Network → `GET /api/equipment/` | `200`, остатки из БД |
| API (изменение) | создать бронирование | `POST /api/reservations/` → `201`, сообщение об успехе |
| БД | перезапустить сервер (`Ctrl+C`, снова `runserver`), обновить страницу | бронирование на месте |
| Права | войти как `student2` | бронирований `student1` не видно; `GET /api/reservations/{id}/` → `404` |
| Автотесты | `python manage.py test accounts` | `Ran 21 tests ... OK` |

Полностью автоматическая проверка в одноразовом окружении: `bash scripts/verify_clean_start.sh`
(в Windows — через Git Bash или WSL).

## 9. Остановка и сброс

- Остановка сервера — `Ctrl+C`.
- Сброс данных: удалить `db.sqlite3` и повторить шаги 5–6.
