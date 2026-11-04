#!/usr/bin/env python3
"""Создание локального .env из .env.example с новым секретным ключом.

    python scripts/make_env.py          # создать .env, если его ещё нет
    python scripts/make_env.py --force  # пересоздать .env заново

Скрипт копирует .env.example в .env и записывает в строку
DJANGO_SECRET_KEY=... случайный ключ (secrets.token_urlsafe). Ключ на экран
не выводится. Работает одинаково в Windows, Linux и macOS, файл сохраняется
в UTF-8 - поэтому не возникает ошибок ручного редактирования (заменена вся
строка вместо значения, файл сохранён в другой кодировке).
"""
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / '.env.example'
TARGET = ROOT / '.env'
REQUIRED = ['DJANGO_SECRET_KEY', 'DJANGO_DEBUG', 'DJANGO_ALLOWED_HOSTS']


def main(argv):
    if TARGET.exists() and '--force' not in argv:
        print('.env уже существует. Чтобы создать заново: python scripts/make_env.py --force')
        return 1
    lines = EXAMPLE.read_text(encoding='utf-8-sig').splitlines()
    key = secrets.token_urlsafe(50)
    result, found = [], False
    for line in lines:
        if line.split('=', 1)[0].strip() == 'DJANGO_SECRET_KEY':
            line, found = f'DJANGO_SECRET_KEY={key}', True
        result.append(line)
    if not found:
        result.append(f'DJANGO_SECRET_KEY={key}')
    TARGET.write_text('\n'.join(result) + '\n', encoding='utf-8')

    names = [l.split('=', 1)[0].strip() for l in result if '=' in l and not l.lstrip().startswith('#')]
    missing = [n for n in REQUIRED if n not in names]
    print(f'Создан {TARGET.name}: ключ DJANGO_SECRET_KEY записан ({len(key)} символов, на экран не выводится)')
    print('Переменные в .env:', ', '.join(names))
    if missing:
        print('ВНИМАНИЕ: в .env.example нет строк', ', '.join(missing), '- сверьте файл с docs/local-setup.md')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
