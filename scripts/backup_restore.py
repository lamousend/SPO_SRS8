#!/usr/bin/env python3
"""Резервная копия, проверка и восстановление данных в учебной среде.

    python scripts/backup_restore.py backup [файл.json]   # снять копию (по умолчанию backups/data-ДАТА.json)
    python scripts/backup_restore.py verify файл.json     # проверить копию на временной пустой базе
    python scripts/backup_restore.py restore файл.json    # загрузить копию в ПУСТУЮ базу и проверить
    python scripts/backup_restore.py check [файл.json]    # проверить целостность текущей базы
                                                         # (и совпадение с копией, если указана)

База выбирается как обычно: DATABASE_URL (PostgreSQL) или локальная SQLite.
Поэтому перенос SQLite -> PostgreSQL выглядит так: backup без DATABASE_URL,
затем migrate и restore с DATABASE_URL нужной базы.

Копия содержит пользователей (с хэшами паролей), справочники, заявки,
бронирования и историю событий. Это ЧУВСТВИТЕЛЬНЫЕ данные: каталог backups/
находится в .gitignore, копии не публикуются и не прикладываются к отчёту.

Коды возврата: 0 - успешно, 1 - ошибка проверки или команды, 2 - неверные аргументы.
"""
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE = ['contenttypes', 'auth.permission', 'sessions', 'admin.logentry']
# модели, по которым сравнивается число записей
TRACKED = ['auth.user', 'auth.group', 'accounts.category', 'accounts.ticket',
           'accounts.equipment', 'accounts.equipmentreservation', 'accounts.reservationevent',
           'accounts.department', 'accounts.course', 'accounts.academicgroup',
           'accounts.studentprofile', 'dashboards.activityevent']


def manage(*args, env=None, quiet=False):
    return subprocess.run([sys.executable, str(ROOT / 'manage.py'), *args], cwd=ROOT,
                          env=env, check=False,
                          stdout=subprocess.DEVNULL if quiet else None)


def counts_in_file(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return Counter(obj['model'] for obj in data)


def django_setup():
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()


def current_counts():
    from django.apps import apps
    return {label: apps.get_model(label).objects.count() for label in TRACKED}


def integrity_problems():
    """Бизнес-инварианты, которые должны выполняться в любой корректной базе."""
    from django.db.models import Sum
    from accounts.models import Equipment, EquipmentReservation, ReservationEvent
    problems = []
    for eq in Equipment.objects.all():
        issued = (EquipmentReservation.objects.filter(equipment=eq, status='issued')
                  .aggregate(total=Sum('quantity'))['total'] or 0)
        if eq.available_q + issued != eq.total_q:
            problems.append(f'{eq.name}: доступно {eq.available_q} + выдано {issued} != всего {eq.total_q}')
        if eq.available_q > eq.total_q:
            problems.append(f'{eq.name}: остаток больше общего количества')
    for res in EquipmentReservation.objects.all():
        actions = set(ReservationEvent.objects.filter(reservation=res).values_list('action', flat=True))
        if 'created' not in actions:
            problems.append(f'бронирование {res.pk}: нет события создания')
        if res.status in ('issued', 'returned') and 'issued' not in actions:
            problems.append(f'бронирование {res.pk}: статус {res.status}, но нет события выдачи')
        if res.status == 'returned' and 'returned' not in actions:
            problems.append(f'бронирование {res.pk}: нет события возврата')
        if res.deleted_at and res.status != 'created':
            problems.append(f'бронирование {res.pk}: удалено не в состоянии created')
    return problems


def cmd_check(expect_file=None):
    django_setup()
    from django.db import connection
    counts = current_counts()
    print(f'база: {connection.vendor} ({connection.settings_dict["NAME"]})')
    ok = True
    if expect_file:
        expected = counts_in_file(expect_file)
        for label in TRACKED:
            mark = 'OK' if counts[label] == expected.get(label, 0) else 'РАСХОЖДЕНИЕ'
            if counts[label] or expected.get(label, 0):
                print(f'  {label:32} в копии {expected.get(label, 0):4}  в базе {counts[label]:4}  {mark}')
            ok &= mark == 'OK'
    else:
        for label in TRACKED:
            if counts[label]:
                print(f'  {label:32} {counts[label]:4}')
    problems = integrity_problems()
    for item in problems:
        print('  нарушение:', item)
    print('остатки и история согласованы' if not problems else f'нарушений: {len(problems)}')
    ok &= not problems
    print('ПРОВЕРКА ПРОЙДЕНА' if ok else 'ПРОВЕРКА НЕ ПРОЙДЕНА')
    return 0 if ok else 1


def database_is_empty():
    django_setup()
    from django.db import connection
    if 'accounts_category' not in connection.introspection.table_names():
        print('Таблиц нет: сначала выполните python manage.py migrate')
        sys.exit(1)
    counts = current_counts()
    return not any(counts.values()), counts


def cmd_backup(target):
    target = Path(target) if target else ROOT / 'backups' / f'data-{datetime.now():%Y%m%d-%H%M%S}.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    args = ['dumpdata', '--natural-foreign', '--natural-primary', '--indent', '2', '--output', str(target)]
    for item in EXCLUDE:
        args += ['--exclude', item]
    if manage(*args).returncode:
        return 1
    counts = counts_in_file(target)
    print(f'Копия сохранена: {target} (объектов: {sum(counts.values())})')
    return 0


def cmd_restore(source, force=False):
    empty, counts = database_is_empty()
    if not empty and not force:
        busy = ', '.join(f'{k}={v}' for k, v in counts.items() if v)
        print(f'База не пустая ({busy}). Восстановление выполняется в пустую базу после migrate; '
              'чтобы загрузить поверх, добавьте --force.')
        return 1
    if manage('loaddata', str(source)).returncode:
        return 1
    # проверка выполняется отдельным процессом, чтобы прочитать уже сохранённые данные
    return subprocess.run([sys.executable, __file__, 'check', str(source)], cwd=ROOT).returncode


def cmd_verify(source):
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, DATABASE_URL=f'sqlite:///{Path(tmp) / "verify.sqlite3"}')
        print('временная пустая база: migrate')
        if manage('migrate', env=env, quiet=True).returncode:
            return 1
        print(f'загрузка копии {source}')
        if manage('loaddata', str(source), env=env).returncode:
            return 1
        return subprocess.run([sys.executable, __file__, 'check', str(source)], cwd=ROOT, env=env).returncode


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    if not args or args[0] not in ('backup', 'restore', 'verify', 'check'):
        print(__doc__)
        return 2
    command, rest = args[0], args[1:]
    if command == 'backup':
        return cmd_backup(rest[0] if rest else None)
    if command == 'check':
        return cmd_check(rest[0] if rest else None)
    if not rest or not Path(rest[0]).is_file():
        print(f'Укажите существующий файл копии: {command} <файл.json>')
        return 2
    if command == 'verify':
        return cmd_verify(rest[0])
    return cmd_restore(rest[0], force='--force' in argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
