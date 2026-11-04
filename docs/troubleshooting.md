# Типичные ошибки

При любой проблеме сначала прочитайте последние строки вывода: в терминале при локальном запуске
или на вкладке Logs на Render. Ошибка 11 найдена при повторном запуске на Windows.

| №  | Что видно | Причина | Как проверить | Что сделать |
|----|-----------|---------|---------------|-------------|
| 1  | ImproperlyConfigured: Set DJANGO_SECRET_KEY при любой команде manage.py | нет файла .env или в нем нет ключа | есть ли файл .env (dir -Force или ls -a) | python scripts/make_env.py; на Render - добавить переменную в Environment |
| 2  | на Render Bad Request (400), в логе DisallowedHost | в DJANGO_ALLOWED_HOSTS не тот адрес | сравнить адрес из лога с переменной | указать адрес сервиса без https:// |
| 3  | collectstatic: файл ...tom-select...css.map не найден | сборщик статики проверяет ссылки внутри файлов Tabler | ошибка называет файл | config/storage.py пропускает ссылки на .map |
| 4  | relation "accounts_ticket" does not exist, страницы с ошибкой 500 | в новой базе не выполнены миграции | showmigrations показывает [ ] | python manage.py migrate (раздел 5 [deployment.md](deployment.md)) |
| 5  | на Render 403 CSRF verification failed при сохранении | DJANGO_CSRF_TRUSTED_ORIGINS не задана или без https:// | на вкладке Network POST - 403 | DJANGO_CSRF_TRUSTED_ORIGINS=https://your-app.onrender.com |
| 6  | GET /api/... - 403 | нет входа в систему | нет cookie sessionid | войти через /accounts/login/ |
| 7  | предупреждение No directory at .../staticfiles/ | статика еще не собрана | пропадает после сборки | локально можно не обращать внимания; перед публикацией - collectstatic |
| 8  | после перезапуска на Render пропали данные | используется SQLite, DATABASE_URL не задана | в настройках нет DATABASE_URL | задать Internal Database URL и выполнить миграции |
| 9  | requirements.txt не читается программами | файл сохранен в UTF-16 (pip freeze в PowerShell) | python scripts/check_docs.py сообщит об этом | пересохранить в UTF-8 |
| 10 | на Render первая страница грузится долго | бесплатный сервис засыпает | в логе новый Booting worker | подождать, проверять через /healthz/ |
| 11 | только в Windows: python -m venv .venv выводит слово Python, папки .venv нет | python указывает на заглушку Microsoft Store | where.exe python показывает ...\WindowsApps\python.exe | py -3.12 -m venv .venv или полный путь к python.exe |

## Проверка по шагам

1. Сервер: откройте /healthz/. Ответ 200 - Django работает, 400 - ошибка в DJANGO_ALLOWED_HOSTS.
2. Статика: страница без оформления - на вкладке Network ищите файлы /static/ с кодом 404.
3. API: на вкладке Network откройте запрос и посмотрите код и текст ответа.
4. База: does not exist - нет миграций; could not connect - неверный DATABASE_URL.
5. Настройки: python manage.py check, перед публикацией python manage.py check --deploy.

## Чего не делать

- Не включать DJANGO_DEBUG=true на Render, чтобы увидеть ошибку. Смотрите логи.
- Не показывать в чатах, отчетах и на скриншотах DATABASE_URL, DJANGO_SECRET_KEY и cookie.
