#!/usr/bin/env python3
"""Локальный прогон шагов CI из .github/workflows/ci.yml.

    python scripts/ci_local.py                          # задание docs-and-sqlite
    python scripts/ci_local.py --postgres postgresql://USER:PASSWORD@localhost:5432
                                                        # + задание postgres на своей PostgreSQL
    python scripts/ci_local.py --install                # выполнить и шаг pip install

Скрипт читает сам ci.yml, поэтому локально выполняются ровно те команды,
что и в GitHub Actions: в чистой копии репозитория (только файлы, которые
попадают в Git), с переменными окружения из workflow. Шаги `uses:`
(checkout, setup-python) заменяются копированием и текущим Python.
Для --postgres пользователь должен иметь право CREATE DATABASE: базы
app, verify и restored пересоздаются. Нужен PyYAML (pip install pyyaml).
"""
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / '.github' / 'workflows' / 'ci.yml'


def repo_files():
    try:
        out = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                             cwd=ROOT, capture_output=True, check=True).stdout
        return [Path(p) for p in out.decode().split('\0') if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        patterns = [l.strip() for l in (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
                    if l.strip() and not l.startswith('#')]
        keep = [p[1:] for p in patterns if p.startswith('!')]
        drop = [p.rstrip('/') for p in patterns if not p.startswith('!')] + ['.git']
        files = []
        for path in ROOT.rglob('*'):
            rel = path.relative_to(ROOT)
            if path.is_dir():
                continue
            parts = rel.parts
            ignored = any(fnmatch.fnmatch(part, pat) for part in parts for pat in drop)
            if ignored and not any(fnmatch.fnmatch(rel.name, k) for k in keep):
                continue
            files.append(rel)
        return files


def expand(value, env, matrix):
    value = str(value)
    value = re.sub(r'\$\{\{\s*env\.(\w+)\s*\}\}', lambda m: env.get(m.group(1), ''), value)
    value = re.sub(r'\$\{\{\s*matrix\.(\w+)\s*\}\}', lambda m: str(matrix.get(m.group(1), '')), value)
    return value


def recreate_databases(base, names):
    import psycopg  # из requirements.txt
    with psycopg.connect(f'{base}/postgres', autocommit=True) as conn:
        for name in names:
            conn.execute(f'DROP DATABASE IF EXISTS {name}')
            conn.execute(f'CREATE DATABASE {name}')
    print(f'    базы пересозданы: {", ".join(names)}')


def run_job(name, job, workflow_env, workdir, install, pg_base):
    matrix = {k: v[0] for k, v in job.get('strategy', {}).get('matrix', {}).items()}
    matrix['python'] = f'{sys.version_info.major}.{sys.version_info.minor} (локальный)'
    env = dict(os.environ)
    for k, v in {**workflow_env, **job.get('env', {})}.items():
        env[k] = expand(v, env, matrix)
    if pg_base:
        env['PG_BASE'] = pg_base
    title = expand(job.get('name', name), env, matrix)
    print(f'\n===== {title} =====')
    results = []
    for step in job['steps']:
        if 'run' not in step:
            continue
        label = step.get('name', step['run'].splitlines()[0])
        if 'pip install -r requirements.txt' in step['run'] and not install:
            results.append(('ПРОПУЩЕН', label, 0.0))
            continue
        step_env = dict(env)
        for k, v in step.get('env', {}).items():
            step_env[k] = expand(v, env, matrix)
        print(f'\n▶ {label}')
        started = time.time()
        if 'psql' in step['run']:
            names = re.findall(r'CREATE DATABASE (\w+)', step['run'])
            recreate_databases(pg_base, names)
            code = 0
        else:
            code = subprocess.run(['bash', '-eo', 'pipefail', '-c', step['run']], cwd=workdir,
                                  env=step_env).returncode
        results.append(('OK' if code == 0 else 'ОШИБКА', label, time.time() - started))
        if code:
            break
    return title, results


def main(argv):
    try:
        import yaml
    except ImportError:
        sys.exit('Нужен PyYAML: python -m pip install pyyaml')
    install = '--install' in argv
    pg_base = argv[argv.index('--postgres') + 1].rstrip('/') if '--postgres' in argv else None
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))
    jobs = ['docs-and-sqlite'] + (['postgres'] if pg_base else [])
    summary, failed = [], False
    with tempfile.TemporaryDirectory() as tmp:
        for job_name in jobs:
            workdir = Path(tmp) / job_name
            for rel in repo_files():
                (workdir / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, workdir / rel)
            title, results = run_job(job_name, workflow['jobs'][job_name], workflow.get('env', {}),
                                     workdir, install, pg_base)
            summary.append((title, results))
            failed |= any(r[0] == 'ОШИБКА' for r in results)
    print('\n===== ИТОГ ЛОКАЛЬНОГО ПРОГОНА CI =====')
    for title, results in summary:
        print(title)
        for status, label, seconds in results:
            print(f'  {status:9} {label} ({seconds:.0f} с)')
    print('CI: ВСЕ ШАГИ ПРОЙДЕНЫ' if not failed else 'CI: ЕСТЬ ОШИБКИ')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
