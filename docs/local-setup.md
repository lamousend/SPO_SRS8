# Локальный запуск с нуля

Выполняйте шаги по порядку. PostgreSQL локально не нужен: без DATABASE_URL используется SQLite.

## 1. Что нужно

| Программа | Версия | Проверка |
|-----------|--------|----------|
| Python | 3.12 или новее | python --version |
| Git | любая | git --version |

## 2. Код и окружение

```bash
git clone https://github.com/lamousend/SPO_SRS8.git
cd SPO_SRS8
python -m venv .venv
```

Если в Windows python -m venv выводит только слово Python и папка .venv не появилась, команда python
указывает на заглушку Microsoft Store. Создайте окружение так:

```powershell
py -3.12 -m venv .venv
```

Активация:

| Система | Команда |
|---------|---------|
| Windows PowerShell | .venv\Scripts\Activate.ps1 (если запрещено: Set-ExecutionPolicy -Scope Process RemoteSigned) |
| Linux, macOS | source .venv/bin/activate |

После активации в начале строки появится (.venv), а python --version покажет версию 3.12 или новее.
В каждом новом окне терминала окружение нужно активировать заново.

## 3. Зависимости

```bash
python -m pip install -r requirements.txt
```

В конце должно появиться Successfully installed.

## 4. Настройка

```bash
python scripts/make_env.py
```

Скрипт создает файл .env из .env.example и записывает в него новый ключ. Ключ на экран не выводится.
Пересоздать файл: python scripts/make_env.py --force.

Если создаете .env вручную (copy .env.example .env), меняйте только значение после знака =:

```text
было:   DJANGO_SECRET_KEY=replace-with-a-long-random-string
стало:  DJANGO_SECRET_KEY=Xq3...ваш_ключ...9Zk
```

Ключ можно получить командой python -c "import secrets; print(secrets.token_urlsafe(50))".
Без ключа проект не запустится (ImproperlyConfigured: Set DJANGO_SECRET_KEY).

Проверка:

```bash
python manage.py check
```

Должно появиться System check identified no issues (0 silenced).

## 5. Миграции

```bash
python manage.py migrate
```

Все строки Applying ... должны заканчиваться на OK.

## 6. Тестовые данные

```bash
python manage.py seed_lab_data --password "ВашПароль123"
python manage.py createsuperuser
```

Создаются 3 категории, оборудование (проектор - 2, ноутбук - 5, графический планшет - 3) и
пользователи student1 и student2. Повторный запуск дубликатов не создает. Администратор нужен для /admin/.

## 7. Запуск

```bash
python manage.py runserver
```

Откройте http://127.0.0.1:8000/accounts/login/ и войдите как student1.

## 8. Проверка

| Что проверить | Как | Результат |
|---------------|-----|-----------|
| Сервер работает | http://127.0.0.1:8000/healthz/ | {"status": "ok"} |
| Интерфейс | страница /reservations/ | форма, остатки и список в оформлении Tabler |
| API (чтение) | вкладка Network в браузере | GET /api/equipment/ - 200 |
| API (запись) | создать бронирование | POST /api/reservations/ - 201 |
| База | перезапустить сервер и обновить страницу | бронирование на месте |
| Доступ | войти как student2 | бронирований student1 не видно, запрос к ним - 404 |
| Автотесты | python manage.py test accounts | Ran 21 tests ... OK |

Полная автоматическая проверка: bash scripts/verify_clean_start.sh (в Windows - через Git Bash или WSL).

## 9. Остановка и сброс

- Остановить сервер - Ctrl+C.
- Начать с пустой базы: удалить db.sqlite3 и повторить шаги 5 и 6.
