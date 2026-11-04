#!/usr/bin/env bash
# Автоматическая проверка «чистого запуска» по документации (СРС 8).
#
#   bash scripts/verify_clean_start.sh                 # новый venv + установка requirements.txt
#   bash scripts/verify_clean_start.sh --skip-install  # зависимости уже установлены (CI, офлайн)
#   VERIFY_DATABASE_URL=postgresql://... bash scripts/verify_clean_start.sh --skip-install
#                                                      # то же самое на пустой PostgreSQL
#
# Что делает скрипт и почему это доказывает воспроизводимость:
#   * копирует во временный каталог ТОЛЬКО файлы, которые попадают в репозиторий
#     (без .env, db.sqlite3, staticfiles/ и прочего из .gitignore) - забытый в Git
#     файл или локальная настройка сразу обнаружатся;
#   * очищает переменные DJANGO_* и DATABASE_URL текущей оболочки и настраивает
#     проект так же, как написано в docs/local-setup.md: python scripts/make_env.py
#     (копия .env.example с новым случайным ключом);
#   * выполняет шаги инструкции: check, migrate, тестовые данные, автотесты,
#     запуск, проверки UI/API/БД, перезапуск, затем production-режим
#     (DEBUG=false, collectstatic, Gunicorn) как в docs/deployment.md.
# Рабочие db.sqlite3 и .env не затрагиваются. Код возврата 0 - все шаги успешны.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
APP="$WORK/SPO_SRS8"
PORT="${PORT:-8765}"
GPORT="${GPORT:-8766}"
PY="${PYTHON:-python3}"
SERVER_PID=""
RESULTS=()
STARTED=$(date +%s)
cleanup() { [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true; rm -rf "$WORK"; }
trap cleanup EXIT

CURRENT=""
step() { CURRENT="$1. $2"; printf '\n[%s] %s\n' "$1" "$2"; }
ok() { RESULTS+=("OK    $CURRENT"); }
fail_report() {
  printf '\nОШИБКА на шаге: %s\n' "$CURRENT"
  printf '%s\n' "${RESULTS[@]}"
}
trap 'fail_report' ERR

# --- 1. чистая копия репозитория ------------------------------------------
step 1 "Чистая копия: только файлы репозитория"
mkdir -p "$APP"
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  (cd "$ROOT" && git ls-files -z --cached --others --exclude-standard | xargs -0 -I{} cp --parents {} "$APP")
  echo "скопировано по git ls-files: $(cd "$APP" && find . -type f | wc -l) файлов"
else
  EXCLUDES=(--exclude=.git)
  while IFS= read -r line; do
    line="${line%%#*}"; line="${line%"${line##*[![:space:]]}"}"
    [ -z "$line" ] || [[ "$line" == !* ]] && continue
    EXCLUDES+=("--exclude=${line%/}")
  done < "$ROOT/.gitignore"
  tar -C "$ROOT" "${EXCLUDES[@]}" --exclude=.env.example.bak -cf - . | tar -C "$APP" -xf -
  # .env.example исключён шаблоном .env.*, но разрешён правилом !.env.example
  cp "$ROOT/.env.example" "$APP/.env.example"
  echo "скопировано с учётом .gitignore: $(cd "$APP" && find . -type f | wc -l) файлов"
fi
for f in .env db.sqlite3 staticfiles; do
  [ ! -e "$APP/$f" ] || { echo "в копию попал локальный файл $f"; exit 1; }
done
echo "в копии нет .env, db.sqlite3, staticfiles/"
ok

# --- 2. окружение и зависимости -------------------------------------------
if [ "${1:-}" != "--skip-install" ]; then
  step 2 "Новое виртуальное окружение и pip install -r requirements.txt"
  "$PY" -m venv "$WORK/venv"
  PY="$WORK/venv/bin/python"
  "$PY" -m pip install -q --upgrade pip
  "$PY" -m pip install -q -r "$APP/requirements.txt"
  "$PY" -m pip list 2>/dev/null | grep -Ei '^(django|djangorestframework|gunicorn|whitenoise|psycopg) '
else
  step 2 "Установка пропущена (--skip-install)"
fi
ok

# --- 3. конфигурация строго по .env.example --------------------------------
step 3 "Конфигурация: python scripts/make_env.py (как в local-setup.md)"
unset DJANGO_SECRET_KEY DJANGO_DEBUG DJANGO_ALLOWED_HOSTS DJANGO_CSRF_TRUSTED_ORIGINS DATABASE_URL
cd "$APP"
"$PY" scripts/make_env.py
if [ -n "${VERIFY_DATABASE_URL:-}" ]; then
  echo "DATABASE_URL=$VERIFY_DATABASE_URL" >> .env
  echo "база: PostgreSQL из VERIFY_DATABASE_URL (значение не выводится)"
else
  echo "база: SQLite в каталоге копии (DATABASE_URL не задана)"
fi
"$PY" manage.py check
ok

step 4 "Миграции"
"$PY" manage.py migrate | tail -3
if "$PY" manage.py showmigrations | grep -q '\[ \]'; then echo "есть невыполненные миграции"; exit 1; fi
echo "showmigrations: все миграции отмечены [X]"
ok

step 5 "Тестовые данные (seed_lab_data)"
"$PY" manage.py seed_lab_data --password 'Verify-pass-2026' | tail -3
ok

step 6 "Автотесты API"
"$PY" manage.py test accounts 2>&1 | grep -E '^(Ran|OK|FAILED)'
ok

start_server() {
  "$PY" manage.py runserver "127.0.0.1:$PORT" --noreload >"$WORK/server.log" 2>&1 &
  SERVER_PID=$!
  for _ in $(seq 1 30); do
    curl -fs "http://127.0.0.1:$PORT/healthz/" >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "Сервер не запустился, журнал:"; cat "$WORK/server.log"; exit 1
}

step 7 "Запуск сервера, /healthz/ и страница входа"
start_server
curl -fs "http://127.0.0.1:$PORT/healthz/"; echo
echo "GET /accounts/login/ -> $(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/accounts/login/")"
ok

step 8 "Вход, GET и изменяющие запросы API"
PORT="$PORT" "$PY" -I scripts/smoke_api.py create
ok

step 9 "Перезапуск сервера и повторное чтение объектов"
kill "$SERVER_PID"; wait "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""
start_server
PORT="$PORT" "$PY" -I scripts/smoke_api.py read
kill "$SERVER_PID"; wait "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""
ok

step 10 "Production-режим: DEBUG=false, collectstatic, Gunicorn"
export DJANGO_DEBUG=false
"$PY" manage.py collectstatic --noinput | tail -1
"$PY" -m gunicorn config.wsgi:application --bind "127.0.0.1:$GPORT" --workers 2 >"$WORK/gunicorn.log" 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 30); do curl -fs "http://127.0.0.1:$GPORT/healthz/" >/dev/null 2>&1 && break; sleep 1; done
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
H=$(code "http://127.0.0.1:$GPORT/healthz/")
CSS=$(code "http://127.0.0.1:$GPORT/static/core/dist/css/tabler.min.css")
BAD=$(code -H 'Host: wrong.example.com' "http://127.0.0.1:$GPORT/healthz/")
NF=$(code "http://127.0.0.1:$GPORT/no-such-page/")
echo "GET /healthz/ -> $H; статика Tabler -> $CSS; чужой Host -> $BAD; несуществующий адрес -> $NF"
[ "$H" = 200 ] && [ "$CSS" = 200 ] && [ "$BAD" = 400 ] && [ "$NF" = 404 ]
ok

trap - ERR
printf '\n===== ИТОГ (%s с) =====\n' "$(( $(date +%s) - STARTED ))"
printf '%s\n' "${RESULTS[@]}"
printf 'ЧИСТЫЙ ЗАПУСК ПОДТВЕРЖДЁН: все шаги выполнены успешно\n'
