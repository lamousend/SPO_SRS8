#!/usr/bin/env python3
"""Проверка комплекта документации (запускается локально и в CI).

    python scripts/check_docs.py

Проверяет, что:
  1. на месте все файлы обязательного комплекта;
  2. requirements.txt в UTF-8, без BOM, все пакеты закреплены через ==;
  3. все переменные окружения из settings.py описаны в .env.example
     и в docs/deployment.md;
  4. .env.example не содержит реальных секретов;
  5. относительные ссылки в Markdown ведут на существующие файлы;
  6. каждый маршрут из docs/api-reference.md описан в docs/api.md;
  7. .env и базы данных исключены через .gitignore;
  8. CHANGELOG.md соответствует формату журнала релизов (scripts/release_notes.py);
  9. docs/openapi.json - корректный JSON с теми же маршрутами, что api-reference.md.
Код возврата 0 - всё в порядке, 1 - найдены проблемы.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = [
    'README.md', 'CHANGELOG.md', '.env.example', 'requirements.txt', 'build.sh',
    'docs/architecture.md', 'docs/project-structure.md', 'docs/database.md',
    'docs/api.md', 'docs/api-reference.md', 'docs/openapi.json', 'docs/local-setup.md',
    'docs/deployment.md', 'docs/troubleshooting.md', 'docs/reproducibility.md',
    'docs/backup-restore.md', 'docs/ci-and-releases.md',
    '.github/workflows/ci.yml', 'scripts/verify_clean_start.sh', 'scripts/backup_restore.py',
    'scripts/release_notes.py', 'scripts/ci_local.py', 'scripts/make_env.py',
]
problems = []


def fail(message):
    problems.append(message)


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


# 1. состав комплекта
for rel in REQUIRED:
    if not (ROOT / rel).is_file():
        fail(f'нет файла {rel}')

# 2. requirements.txt
raw = (ROOT / 'requirements.txt').read_bytes() if (ROOT / 'requirements.txt').is_file() else b''
if raw.startswith((b'\xff\xfe', b'\xfe\xff', b'\xef\xbb\xbf')):
    fail('requirements.txt содержит BOM/UTF-16: сохраните в UTF-8 без BOM')
else:
    for number, line in enumerate(raw.decode('utf-8').splitlines(), 1):
        if line.strip() and not line.startswith('#') and '==' not in line:
            fail(f'requirements.txt:{number}: версия не закреплена ({line})')

# 3. переменные окружения
settings_text = read('config/settings.py')
variables = sorted(set(re.findall(r'os\.environ\.get\(\s*"([A-Z_]+)"', settings_text)) | {'DATABASE_URL'})
env_example = read('.env.example') if (ROOT / '.env.example').is_file() else ''
deployment = read('docs/deployment.md') if (ROOT / 'docs/deployment.md').is_file() else ''
for name in variables:
    if name not in env_example:
        fail(f'{name} не описана в .env.example')
    if name not in deployment:
        fail(f'{name} не описана в docs/deployment.md')

# 4. секреты в образце
for pattern, what in [(r'django-insecure', 'ключ django-insecure'),
                      (r'dpg-[a-z0-9]{8,}', 'внутренний хост Render'),
                      (r'postgres(ql)?://[^\s:]+:(?!PASSWORD)[^\s@]+@', 'пароль в DATABASE_URL')]:
    if re.search(pattern, env_example):
        fail(f'.env.example: похоже на реальный секрет ({what})')

# 5. ссылки в Markdown
markdown_files = [ROOT / 'README.md', ROOT / 'CHANGELOG.md', *sorted((ROOT / 'docs').glob('*.md'))]
for md in markdown_files:
    if not md.is_file():
        continue
    for target in re.findall(r'\]\(([^)\s]+)\)', md.read_text(encoding='utf-8')):
        if re.match(r'^(https?:|mailto:|#)', target):
            continue
        path = (md.parent / target.split('#')[0]).resolve()
        if not path.exists():
            fail(f'{md.relative_to(ROOT)}: битая ссылка {target}')

# 6. покрытие маршрутов карточками
if (ROOT / 'docs/api-reference.md').is_file() and (ROOT / 'docs/api.md').is_file():
    api_text = read('docs/api.md')
    for url in sorted(set(re.findall(r'^\| [A-Z]+ \| (/api/\S+) \|', read('docs/api-reference.md'), flags=re.M))):
        short = url.replace('{pk}', '{id}')
        if url not in api_text and short not in api_text:
            fail(f'маршрут {url} не описан в docs/api.md')

# 7. .gitignore
ignore = read('.gitignore') if (ROOT / '.gitignore').is_file() else ''
for entry in ('.env', 'db.sqlite3'):
    if entry not in ignore.splitlines():
        fail(f'.gitignore не исключает {entry}')

# 8. журнал изменений релизов
sys.path.insert(0, str(ROOT / 'scripts'))
import release_notes  # noqa: E402
if (ROOT / 'CHANGELOG.md').is_file():
    problems.extend(release_notes.problems_in(release_notes.parse(read('CHANGELOG.md'))))

# 9. схема OpenAPI
if (ROOT / 'docs/openapi.json').is_file():
    import json
    try:
        spec = json.loads(read('docs/openapi.json'))
        documented = set(spec.get('paths', {}))
        referenced = set(re.findall(r'^\| [A-Z]+ \| (/api/\S+) \|', read('docs/api-reference.md'), flags=re.M))
        if spec.get('openapi', '').split('.')[0] != '3':
            fail('docs/openapi.json: не OpenAPI 3')
        if documented != referenced:
            fail(f'docs/openapi.json и api-reference.md расходятся: {sorted(documented ^ referenced)}')
    except ValueError as error:
        fail(f'docs/openapi.json: некорректный JSON ({error})')

if problems:
    print('Найдены проблемы документации:')
    for item in problems:
        print(' -', item)
    sys.exit(1)
print(f'Документация в порядке: проверено файлов - {len(REQUIRED)}, '
      f'переменных окружения - {len(variables)}')
