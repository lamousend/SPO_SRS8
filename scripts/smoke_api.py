#!/usr/bin/env python3
"""Дымовая проверка API по HTTP (только стандартная библиотека).

    smoke_api.py create   - войти как student1: GET справочников, создание заявки,
                            создание и выдача бронирования
    smoke_api.py read     - войти снова и убедиться, что заявка, выданное
                            бронирование и уменьшенный остаток сохранились

Пароль и порт берутся из окружения (PORT) или значений по умолчанию
скрипта verify_clean_start.sh. Секреты в вывод не попадают.
"""
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"
USER = os.environ.get('SMOKE_USER', 'student1')
PASSWORD = os.environ.get('SMOKE_PASSWORD', 'Verify-pass-2026')
TITLE = 'Проверка чистого запуска'
PURPOSE = 'Проверка чистого запуска'


def login():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    page = opener.open(BASE + '/accounts/login/').read().decode()
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page).group(1)
    data = urllib.parse.urlencode({'username': USER, 'password': PASSWORD,
                                   'csrfmiddlewaretoken': token}).encode()
    opener.open(urllib.request.Request(
        BASE + '/accounts/login/', data, {'Referer': BASE + '/accounts/login/'}))
    return opener, jar


def call(session, method, path, body=None):
    opener, jar = session
    csrf = next((c.value for c in jar if c.name == 'csrftoken'), '')
    request = urllib.request.Request(
        BASE + path, json.dumps(body).encode() if body is not None else None,
        {'Content-Type': 'application/json', 'X-CSRFToken': csrf, 'Referer': BASE + '/'},
        method=method)
    try:
        response = opener.open(request)
    except urllib.error.HTTPError as error:
        response = error
    raw = response.read().decode()
    status = response.status if hasattr(response, 'status') else response.code
    print(f'{method} {path} -> {status}')
    return status, (json.loads(raw) if raw else None)


def main(mode):
    session = login()
    if mode == 'create':
        status, categories = call(session, 'GET', '/api/categories/')
        assert status == 200 and categories, 'категории не найдены (выполнен ли seed_lab_data?)'
        status, ticket = call(session, 'POST', '/api/tickets/',
                              {'title': TITLE, 'category': categories[0]['id']})
        assert status == 201 and ticket['status'] == 'new', 'заявка не создана'
        status, _ = call(session, 'PATCH', f"/api/tickets/{ticket['id']}/", {'status': 'progress'})
        assert status == 200, 'статус заявки не изменён'
        status, equipment = call(session, 'GET', '/api/equipment/')
        assert status == 200 and equipment, 'оборудование не найдено'
        item = equipment[0]
        status, reservation = call(session, 'POST', '/api/reservations/',
                                   {'purpose': PURPOSE, 'equipment': item['id'], 'quantity': 1})
        assert status == 201, 'бронирование не создано'
        status, issued = call(session, 'POST', f"/api/reservations/{reservation['id']}/issue/")
        assert status == 200 and issued['status'] == 'issued', 'оборудование не выдано'
        print(f"создана заявка id={ticket['id']}, выдано бронирование id={reservation['id']} "
              f"({item['name']}: остаток был {item['available_q']})")
    elif mode == 'read':
        status, tickets = call(session, 'GET', '/api/tickets/?status=progress')
        assert status == 200 and any(t['title'] == TITLE for t in tickets), \
            'заявка не найдена после перезапуска'
        status, reservations = call(session, 'GET', '/api/reservations/?status=issued')
        found = [r for r in reservations if r['purpose'] == PURPOSE]
        assert status == 200 and found, 'бронирование не найдено после перезапуска'
        status, equipment = call(session, 'GET', '/api/equipment/')
        item = next(e for e in equipment if e['id'] == found[0]['equipment'])
        assert item['available_q'] == item['total_q'] - found[0]['quantity'], 'остаток не сохранился'
        status, history = call(session, 'GET', f"/api/reservations/{found[0]['id']}/history/")
        actions = [e['action'] for e in history]
        assert actions == ['created', 'issued'], f'история: {actions}'
        print(f"после перезапуска: заявка в работе, бронирование выдано, остаток {item['name']} "
              f"{item['available_q']} из {item['total_q']}, история {actions} - данные сохраняются")
    else:
        sys.exit('режим: create или read')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'create')
