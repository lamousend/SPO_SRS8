# Облачное развёртывание (Render + PostgreSQL)

Инструкция соответствует ПЗ № 8. Используются бесплатные ресурсы Render. Фактические
секреты, пароли и адреса баз в документацию и репозиторий **не вносятся**.

## 1. Схема

Браузер → HTTPS → Render Web Service → Gunicorn → Django/DRF → PostgreSQL;
статику выдаёт WhiteNoise (см. [architecture.md](architecture.md)).

## 2. Переменные окружения

| Переменная | Назначение | Значение на Render |
|------------|------------|--------------------|
| `DJANGO_SECRET_KEY` | секретный ключ: подпись сессий и токенов. Без неё проект не стартует | сгенерировать (кнопка Generate на Render) |
| `DJANGO_DEBUG` | `true` показывает подробные ошибки и накапливает запросы в памяти. В эксплуатации запрещено | `false` |
| `DJANGO_ALLOWED_HOSTS` | домены, на которые отвечает Django; чужой `Host` → `400 DisallowedHost` | `your-app.onrender.com` (без `https://`) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | HTTPS-источники для проверки CSRF при `POST`/`PATCH`/`DELETE` | `https://your-app.onrender.com` (со схемой) |
| `DATABASE_URL` | подключение к PostgreSQL; обработка — `dj-database-url` | **Internal Database URL** из карточки БД |

Правила:

- `DATABASE_URL` содержит пароль. Его значение нельзя публиковать, коммитить и вставлять в отчёт —
  на скриншотах значения переменных скрываются.
- **Internal Database URL** действует только внутри сети Render (веб-сервис ↔ БД в одном регионе) —
  его указывают у веб-сервиса. **External Database URL** нужен для подключения с вашего компьютера
  (разовые миграции); его не сохраняют в файлах и закрывают окно терминала после работы.
- Образец имён и безопасных значений — `.env.example`.

## 3. Создание PostgreSQL

1. Render → **New → PostgreSQL**.
2. Имя, например `pz8-django-db`; регион — тот же, что у веб-сервиса (в ПЗ 8 — Oregon); тариф **Free**.
3. После создания в карточке БД скопируйте *Internal Database URL* (для веб-сервиса).

## 4. Создание Web Service

1. Render → **New → Web Service** → подключить репозиторий GitHub.
2. Параметры:

| Поле | Значение |
|------|----------|
| Language | Python 3 |
| Region | как у БД |
| Instance Type | Free |
| Build Command | `bash build.sh` |
| Start Command | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |
| Health Check Path (необязательно) | `/healthz/` |

3. В разделе Environment добавьте пять переменных из таблицы выше.

## 5. Разделение процессов

| Этап | Когда | Команда | Что делает |
|------|-------|---------|------------|
| Сборка | при каждом деплое | `bash build.sh` = `pip install -r requirements.txt` + `python manage.py collectstatic --noinput` | ставит зависимости, собирает статику в `staticfiles/` |
| Миграции | после появления БД и при изменении моделей | `python manage.py migrate` | создаёт/обновляет таблицы |
| Запуск | при старте сервиса | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` | запускает Django |
| Проверка | после деплоя | `GET /healthz/`, страница входа, API | см. раздел 7 |

Миграции в ПЗ 8 выполнены один раз **с локального компьютера** (на бесплатном тарифе консоль сервиса недоступна).
В отдельном окне терминала, не записывая значение в файлы:

```powershell
# Windows PowerShell
$env:DATABASE_URL = "<External Database URL из Render>"
$env:DJANGO_SECRET_KEY = "temporary-local-value"
python manage.py migrate
python manage.py showmigrations
python manage.py createsuperuser
```
```bash
# Linux / macOS
DATABASE_URL='<External Database URL из Render>' DJANGO_SECRET_KEY=temporary python manage.py migrate
```

Затем закройте терминал. Если у плана есть Pre-Deploy Command, `python manage.py migrate` можно задать там.
Тестовые данные в облаке: категории и оборудование добавляются через `/admin/` суперпользователя
(или командой `seed_lab_data` тем же способом).

## 6. Локальная SQLite и облачная PostgreSQL

Это **разные базы**. Данные, созданные локально, в облаке не появятся, и данные облака не попадают в `db.sqlite3`.
Диск веб-сервиса на Render временный: SQLite-файл там пропал бы при перезапуске, поэтому в облаке
используется только PostgreSQL. Перенос данных — [backup-restore.md](backup-restore.md).

## 7. Проверка работы

| № | Проверка | Ожидание |
|---|----------|----------|
| 1 | статус сервиса | `Live`; в логе `Listening at: http://0.0.0.0:...` и `Booting worker` |
| 2 | `GET https://your-app.onrender.com/healthz/` | `200`, `{"status": "ok"}` |
| 3 | страница входа | открывается по HTTPS с оформлением Tabler (статика без `404`) |
| 4 | вход и `GET /api/categories/` | `200`, данные из PostgreSQL |
| 5 | `POST /api/tickets/` или `/api/reservations/` из интерфейса | `201` |
| 6 | **Manual Deploy → Restart**, затем обновить страницу | созданная запись сохранилась |
| 7 | несуществующий адрес при `DJANGO_DEBUG=false` | краткая страница Not Found без отладочной информации |

На бесплатном тарифе неактивный сервис может «засыпать»: первый запрос после паузы выполняется заметно дольше.

## 8. Проверка настроек безопасности

```bash
DJANGO_DEBUG=false python manage.py check --deploy
```

Предупреждения `security.W004`, `W008`, `W012`, `W016` относятся к HTTPS-настройкам, которые обеспечивает
платформа (`SECURE_PROXY_SSL_HEADER` уже задан); `W009` появляется, если ключ короче 50 символов или имеет мало уникальных символов —
при необходимости задайте более длинный ключ (`python -c "import secrets; print(secrets.token_urlsafe(64))"`).

## 9. Ошибки при развёртывании

См. [troubleshooting.md](troubleshooting.md).
