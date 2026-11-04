#!/usr/bin/env python3
"""Журнал изменений релизов: проверка CHANGELOG.md и текст для выпуска.

    python scripts/release_notes.py --check        # проверить формат журнала
    python scripts/release_notes.py 0.5.0          # напечатать раздел версии 0.5.0
    python scripts/release_notes.py v0.5.0 --tag   # то же; заодно проверить, что это
                                                   # последняя версия (для тега в CI)

Формат журнала (Keep a Changelog + семантическое версионирование):
    ## [Не выпущено]                         - необязательный раздел будущих изменений
    ## [X.Y.Z] - ГГГГ-ММ-ДД - описание        - выпуск; версии и даты идут по убыванию
    ### Добавлено | Изменено | Исправлено | Удалено | Безопасность
    - пункт изменения
Версия последнего выпуска используется как версия API в docs/openapi.json.
"""
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / 'CHANGELOG.md'
SECTIONS = {'Добавлено', 'Изменено', 'Исправлено', 'Удалено', 'Безопасность'}
HEADER = re.compile(r'^## \[(?P<version>[^\]]+)\](?: [—-] (?P<date>\d{4}-\d{2}-\d{2}))?(?: [—-] (?P<title>.+))?$')


def parse(text):
    releases, current = [], None
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith('## '):
            match = HEADER.match(line)
            current = {'line': number, 'raw': line, 'match': match, 'body': [],
                       'version': match.group('version') if match else None,
                       'date': match.group('date') if match else None}
            releases.append(current)
        elif current is not None:
            current['body'].append(line)
    return releases


def problems_in(releases):
    problems, previous = [], None
    if not releases:
        return ['в CHANGELOG.md нет ни одного раздела ## [версия]']
    for index, rel in enumerate(releases):
        where = f"CHANGELOG.md:{rel['line']}"
        if not rel['match']:
            problems.append(f"{where}: заголовок не по формату '## [X.Y.Z] - ГГГГ-ММ-ДД - описание'")
            continue
        if rel['version'] == 'Не выпущено':
            if index != 0:
                problems.append(f'{where}: раздел [Не выпущено] должен быть первым')
            continue
        if not re.fullmatch(r'\d+\.\d+\.\d+', rel['version']):
            problems.append(f"{where}: версия {rel['version']} не в формате X.Y.Z")
            continue
        if not rel['date']:
            problems.append(f"{where}: у версии {rel['version']} нет даты выпуска")
        else:
            try:
                released = date.fromisoformat(rel['date'])
                if released > date.today():
                    problems.append(f"{where}: дата {rel['date']} в будущем")
            except ValueError:
                problems.append(f"{where}: неверная дата {rel['date']}")
        sections = [l[4:].strip() for l in rel['body'] if l.startswith('### ')]
        if not sections:
            problems.append(f"{where}: у версии {rel['version']} нет разделов ### Добавлено/Исправлено/...")
        for name in sections:
            if name not in SECTIONS:
                problems.append(f'{where}: неизвестный раздел «{name}» (допустимы: {", ".join(sorted(SECTIONS))})')
        if not any(l.startswith('- ') for l in rel['body']):
            problems.append(f"{where}: у версии {rel['version']} нет ни одного пункта")
        key = tuple(int(x) for x in rel['version'].split('.'))
        if previous:
            if key >= previous[0]:
                problems.append(f"{where}: версия {rel['version']} должна быть меньше {previous[1]} (порядок по убыванию)")
            if rel['date'] and previous[2] and rel['date'] > previous[2]:
                problems.append(f"{where}: дата {rel['date']} позже, чем у более новой версии")
        previous = (key, rel['version'], rel['date'])
    return problems


def released(releases):
    return [r for r in releases if r['match'] and r['version'] != 'Не выпущено']


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    releases = parse(CHANGELOG.read_text(encoding='utf-8'))
    problems = problems_in(releases)
    if '--check' in argv or not args:
        if problems:
            print('CHANGELOG.md: найдены проблемы')
            for item in problems:
                print(' -', item)
            return 1
        latest = released(releases)[0]
        print(f"CHANGELOG.md в порядке: выпусков {len(released(releases))}, "
              f"последний {latest['version']} от {latest['date']}")
        return 0
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        return 1
    version = args[0].lstrip('v')
    found = [r for r in released(releases) if r['version'] == version]
    if not found:
        print(f'версии {version} нет в CHANGELOG.md', file=sys.stderr)
        return 1
    if '--tag' in argv and released(releases)[0]['version'] != version:
        print(f"тег v{version} не совпадает с последней версией журнала "
              f"{released(releases)[0]['version']}", file=sys.stderr)
        return 1
    rel = found[0]
    title = rel['match'].group('title') or ''
    print(f"## {version} ({rel['date']}){' - ' + title if title else ''}")
    print('\n'.join(rel['body']).strip())
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
