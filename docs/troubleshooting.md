# Типичные ошибки и диагностика

Первое, что нужно сделать при любой проблеме: прочитать **последние строки журнала** — вывод `manage.py`/`runserver`
локально или вкладку **Logs** сервиса на Render. Ошибки 1 и 7 воспроизведены при подготовке документации
на чистой копии проекта; 2 и 3 возникли и были устранены в ПЗ № 8; 11 и 12 найдены при повторном запуске на Windows.

| № | Симптом | Причина | Диагностика | Исправление |
|---|---------|---------|-------------|-------------|
| 1 | `django.core.exceptions.ImproperlyConfigured: Set DJANGO_SECRET_KEY` при любой команде `manage.py` | переменная не задана, файл `.env` не создан | `ls -a` / `dir -Force`: есть ли `.env`; `echo $DJANGO_SECRET_KEY` | `cp .env.example .env`, подставить ключ; в облаке — добавить переменную в Environment |
| 2 | Render: `Bad Request (400)`; в логе `DisallowedHost: Invalid HTTP_HOST header` | в `DJANGO_ALLOWED_HOSTS` указан не тот домен | сравнить домен из лога с переменной | указать фактический домен сервиса без `https://`, сохранить и дождаться перезапуска |
| 3 | `collectstatic`: `ValueError: The file '...tom-select...css.map' could not be found` | `CompressedManifestStaticFilesStorage` проверяет ссылки внутри CSS/JS, библиотеки Tabler ссылаются на отсутствующие `.map` и картинки | текст ошибки называет файл | использовать `config/storage.py` (пропускает `.map`), добавить недостающие файлы в `static/` |
| 4 | `ProgrammingError: relation "accounts_ticket" does not exist`, страницы падают с 500 | в новой пустой PostgreSQL не выполнены миграции | в логе имя таблицы; `showmigrations` с `DATABASE_URL` базы показывает `[ ]` | выполнить `python manage.py migrate` (раздел 5 [deployment.md](deployment.md)) |
| 5 | в облаке `403 Forbidden`, `CSRF verification failed` при создании/изменении; чтения работают | `DJANGO_CSRF_TRUSTED_ORIGINS` не задана или без `https://` | Network: `POST` → `403`; тело ответа про CSRF | `DJANGO_CSRF_TRUSTED_ORIGINS=https://your-app.onrender.com` |
| 6 | `GET /api/...` → `403 {"detail": "..."}` | нет входа в систему (сессия) | открыть `/accounts/login/`; Network → cookie `sessionid` | войти; в скриптах сначала получить сессию, как в `scripts/smoke_api.py` |
| 7 | при `check`/`test`/`runserver` предупреждение `UserWarning: No directory at: .../staticfiles/` | WhiteNoise ищет `STATIC_ROOT`, который ещё не создан | предупреждение исчезает после сборки | локально можно игнорировать; перед эксплуатацией выполнить `python manage.py collectstatic --noinput` |
| 8 | после «Restart» на Render данные исчезли | используется SQLite на временном диске, `DATABASE_URL` не задана | `showmigrations`/`settings.DATABASES` — ENGINE `sqlite3` | задать `DATABASE_URL` (Internal URL PostgreSQL), выполнить миграции заново |
| 9 | `requirements.txt` в UTF-16 (так было в исходном проекте): файл не читается редакторами, сервисами проверки зависимостей и некоторыми версиями инструментов | `pip freeze > requirements.txt` в Windows PowerShell 5.x записывает UTF-16; pip с BOM обычно справляется, остальные инструменты — нет | `file requirements.txt`; `python scripts/check_docs.py` сообщает о BOM/UTF-16 | пересохранить в UTF-8 без BOM; создавать так: `pip freeze \| Out-File -Encoding utf8` (затем убрать BOM) или выполнять `pip freeze` в Git Bash |
| 10 | на Render первая страница после паузы открывается очень долго | бесплатный сервис останавливается при простое | в логе новый `Booting worker` | подождать; для проверки использовать `/healthz/` |
| 11 | Windows: `collectstatic` → `The file '...typed.umd.js.map' could not be found`, хотя в Linux и на Render сборка проходит | Git в Windows при `clone` заменил переводы строк на CRLF; в ссылке `sourceMappingURL` остаётся невидимый `\r`, и пропуск `.map` в `config/storage.py` не срабатывал | ошибка только на Windows-клоне; `git config core.autocrlf` → `true` | исправлено в 0.5.1: `config/storage.py` обрезает пробельные символы ссылки, `.gitattributes` хранит `static/` байт-в-байт и `*.sh` с LF |
| 12 | Windows: `python -m venv .venv` выводит только `Python`, `.venv` не создаётся | `python` указывает на заглушку Microsoft Store, а не на установленный Python | `where.exe python` — первым идёт `...\WindowsApps\python.exe` | `py -3.12 -m venv .venv` или полный путь к `python.exe`; либо отключить псевдонимы в «Параметры → Приложения → Псевдонимы выполнения приложений» |

## Как диагностировать по слоям

1. **Сеть/хост**: `curl -i https://your-app.onrender.com/healthz/` — `200` значит, что Django запущен; `400` — `ALLOWED_HOSTS`.
2. **Статика**: страница без оформления → вкладка Network, файлы `/static/...` с `404` → не выполнен `collectstatic`.
3. **API**: Network → запрос → вкладки Headers/Response; код и тело ошибки в формате из [api.md](api.md).
4. **БД**: сообщение `relation ... does not exist` — миграции; `could not connect` — неверный `DATABASE_URL` или регион.
5. **Конфигурация**: `python manage.py check` локально; `python manage.py check --deploy` перед публикацией.

## Чего не делать при диагностике

- Не включать `DJANGO_DEBUG=true` в облаке «для просмотра ошибки» — используйте логи.
- Не вставлять в чаты, отчёты и скриншоты значения `DATABASE_URL`, `DJANGO_SECRET_KEY`, cookie `sessionid`/`csrftoken`.
