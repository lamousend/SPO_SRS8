# Публикация на Render

Инструкция повторяет ПЗ № 8 и использует бесплатные ресурсы Render. Настоящие ключи, пароли
и адреса баз в документацию и репозиторий не вносятся.

## 1. Схема

Браузер - HTTPS - Render Web Service - Gunicorn - Django и DRF - PostgreSQL. Статику отдает WhiteNoise
(см. [architecture.md](architecture.md)).

## 2. Переменные окружения

| Переменная | Назначение | Значение на Render |
|------------|------------|--------------------|
| DJANGO_SECRET_KEY | секретный ключ; без него проект не запускается | создать кнопкой Generate |
| DJANGO_DEBUG | режим отладки, в работе запрещен | false |
| DJANGO_ALLOWED_HOSTS | адреса, на которые отвечает сайт; чужой адрес - ошибка 400 | your-app.onrender.com (без https://) |
| DJANGO_CSRF_TRUSTED_ORIGINS | адреса, с которых можно отправлять формы и POST-запросы | https://your-app.onrender.com |
| DATABASE_URL | подключение к PostgreSQL | Internal Database URL из карточки базы |

Правила:

- В DATABASE_URL есть пароль. Его нельзя публиковать, хранить в Git и показывать на скриншотах.
- Internal Database URL работает только внутри Render. Его указывают у веб-сервиса.
- External Database URL нужен только для разовых миграций со своего компьютера. В файлы его не записывают.
- Образец имен переменных - в файле .env.example.

## 3. База PostgreSQL

1. Render - New - PostgreSQL.
2. Имя, например pz8-django-db; регион как у веб-сервиса (Oregon); тариф Free.
3. Скопируйте Internal Database URL из карточки базы.

## 4. Web Service

1. Render - New - Web Service, подключите репозиторий GitHub.
2. Заполните поля:

| Поле | Значение |
|------|----------|
| Language | Python 3 |
| Region | как у базы |
| Instance Type | Free |
| Build Command | bash build.sh |
| Start Command | gunicorn config.wsgi:application --bind 0.0.0.0:$PORT |
| Health Check Path | /healthz/ |

3. В разделе Environment добавьте пять переменных из раздела 2.

## 5. Этапы

| Этап | Когда | Команда |
|------|-------|---------|
| Сборка | при каждой публикации | bash build.sh (установка зависимостей и collectstatic) |
| Миграции | после создания базы и при изменении моделей | python manage.py migrate |
| Запуск | при старте сервиса | gunicorn config.wsgi:application --bind 0.0.0.0:$PORT |
| Проверка | после публикации | /healthz/, страница входа, запросы к API |

На бесплатном тарифе консоли нет, поэтому миграции выполняются один раз со своего компьютера.
Адрес базы задается только в текущем окне терминала:

```powershell
# Windows PowerShell
$env:DATABASE_URL = "<External Database URL из Render>"
python manage.py migrate
python manage.py createsuperuser
```
```bash
# Linux, macOS
DATABASE_URL='<External Database URL из Render>' python manage.py migrate
```

После этого закройте окно терминала. Категории и оборудование добавьте в /admin/.

## 6. Локальная и облачная база

Это разные базы. Данные из SQLite не попадают на Render, и наоборот. Диск веб-сервиса на Render
временный, поэтому SQLite там потеряла бы данные при перезапуске. Перенос данных - в
[backup-restore.md](backup-restore.md).

## 7. Проверка

| № | Что проверить | Результат |
|---|---------------|-----------|
| 1 | статус сервиса | Live, в логе Booting worker |
| 2 | https://your-app.onrender.com/healthz/ | 200, {"status": "ok"} |
| 3 | страница входа | открывается по HTTPS с оформлением |
| 4 | вход и GET /api/categories/ | 200, данные из PostgreSQL |
| 5 | создание записи в интерфейсе | 201 |
| 6 | Manual Deploy - Restart, затем обновить страницу | запись осталась |
| 7 | несуществующий адрес | короткая страница Not Found без отладки |

Бесплатный сервис засыпает без запросов, поэтому первая загрузка после паузы долгая.

## 8. Проверка настроек безопасности

```bash
python manage.py check --deploy
```

Предупреждения W004, W008, W012 и W016 касаются HTTPS, который дает Render. W009 появляется при коротком ключе.

## 9. Ошибки

См. [troubleshooting.md](troubleshooting.md).
