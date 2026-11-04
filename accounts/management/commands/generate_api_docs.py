"""Автоматическая генерация описания REST API из кода проекта.

    python manage.py generate_api_docs            # записать оба файла
    python manage.py generate_api_docs --check    # проверить, что файлы актуальны (CI)

Создаются:
  docs/api-reference.md - справочник: маршруты, параметры отбора, поля данных;
  docs/openapi.json     - машиночитаемая схема OpenAPI 3.0 (можно открыть
                          в Swagger Editor, Postman, Insomnia).

Источник - DefaultRouter из accounts/urls.py, сериализаторы DRF, модели,
docstring-и ViewSet'ов и атрибут api_query_params. Поэтому описать
вымышленный маршрут или забыть новый невозможно: при изменении кода
проверка --check в CI сообщит, что документация устарела.
"""
import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rest_framework import serializers

from accounts.urls import router

DOCS = Path(settings.BASE_DIR) / 'docs'
REFERENCE = DOCS / 'api-reference.md'
OPENAPI = DOCS / 'openapi.json'
CHANGELOG = Path(settings.BASE_DIR) / 'CHANGELOG.md'


def release_version():
    """Версия API = последний выпуск в CHANGELOG.md (раздел [Не выпущено] пропускается)."""
    text = CHANGELOG.read_text(encoding='utf-8') if CHANGELOG.is_file() else ''
    match = re.search(r'^## \[(\d+\.\d+\.\d+)\]', text, flags=re.M)
    return match.group(1) if match else '0.0.0'

METHOD_ORDER = ['get', 'post', 'put', 'patch', 'delete']
STANDARD = {'list', 'create', 'retrieve', 'update', 'partial_update', 'destroy'}
ACTION_TITLES = {
    'list': 'список объектов',
    'create': 'создание объекта',
    'retrieve': 'получение объекта',
    'update': 'полное изменение',
    'partial_update': 'частичное изменение',
    'destroy': 'удаление',
}
SUCCESS = {'create': '201', 'destroy': '204'}


# ---------- поля сериализаторов -> JSON Schema ----------
def field_schema(field):
    """Тип поля DRF в терминах OpenAPI."""
    if isinstance(field, serializers.ChoiceField):
        return {'type': 'string', 'enum': [str(c) for c in field.choices]}
    if isinstance(field, serializers.PrimaryKeyRelatedField):
        return {'type': 'integer'}
    if isinstance(field, (serializers.IntegerField,)):
        schema = {'type': 'integer'}
        min_value = getattr(field, 'min_value', None)
        if min_value is not None:
            schema['minimum'] = min_value
        return schema
    if isinstance(field, serializers.DateTimeField):
        return {'type': 'string', 'format': 'date-time'}
    if isinstance(field, serializers.BooleanField):
        return {'type': 'boolean'}
    schema = {'type': 'string'}
    max_length = getattr(field, 'max_length', None)
    if max_length:
        schema['maxLength'] = max_length
    return schema


def field_description(field, serializer):
    if field.help_text:
        return str(field.help_text)
    model = getattr(serializer.Meta, 'model', None)
    source = field.source if field.source != '*' else field.field_name
    if model is not None and '.' not in source:
        try:
            return str(model._meta.get_field(source).verbose_name)
        except Exception:
            pass
    if '.' in source:
        return f'из связанного объекта ({source})'
    return source.replace('_', ' ')


def schema_name(serializer_class):
    return serializer_class.__name__.removesuffix('Serializer')


def describe_serializer(serializer_class):
    """Возвращает (schema, request_schema, rows) для сериализатора."""
    serializer = serializer_class()
    props, request_props, required, rows = {}, {}, [], []
    for name, field in serializer.fields.items():
        schema = field_schema(field)
        desc = field_description(field, serializer)
        props[name] = dict(schema, description=desc)
        if field.read_only:
            props[name]['readOnly'] = True
        else:
            request_props[name] = dict(schema, description=desc)
            if field.required:
                required.append(name)
        type_text = schema.get('type')
        if 'enum' in schema:
            type_text = ' \\| '.join(schema['enum'])
        elif schema.get('format'):
            type_text = schema['format']
        rows.append((name, type_text,
                     'только чтение' if field.read_only else ('обязательно' if field.required else 'необязательно'),
                     desc))
    response = {'type': 'object', 'properties': props}
    request = {'type': 'object', 'properties': request_props}
    if required:
        request['required'] = required
    return response, request, rows


# ---------- маршруты ----------
def path_template(pattern):
    text = str(pattern.pattern).lstrip('^').rstrip('$')
    text = re.sub(r'\(\?P<(\w+)>[^)]+\)', r'{\1}', text)
    return '/api/' + text.replace('{pk}', '{id}')


def first_line(text):
    return (text or '').strip().split('\n')[0].strip()


def collect():
    routes = []
    for pattern in router.urls:
        callback = getattr(pattern, 'callback', None)
        actions = getattr(callback, 'actions', None)
        if not actions or '\\.' in str(pattern.pattern):
            continue  # корень API и суффиксы формата (.json)
        view_class = callback.cls
        initkwargs = getattr(callback, 'initkwargs', {}) or {}
        for method in METHOD_ORDER:
            if method not in actions:
                continue
            action = actions[method]
            handler = getattr(view_class, action)
            routes.append({
                'url': path_template(pattern),
                'method': method,
                'action': action,
                'view': view_class,
                'handler': f'{view_class.__name__}.{action}',
                'serializer': initkwargs.get('serializer_class') or view_class.serializer_class,
                'summary': (ACTION_TITLES.get(action) if action in STANDARD else None)
                           or first_line(handler.__doc__).rstrip('.').replace(' -> ', ' - ') or action,
                'is_list': action == 'list' or (action not in STANDARD and method == 'get'),
                'has_body': action in ('create', 'update', 'partial_update'),
                'detail': '{id}' in path_template(pattern),
            })
    routes.sort(key=lambda r: (r['url'], METHOD_ORDER.index(r['method'])))
    return routes


def permission_names(view_class):
    classes = getattr(view_class, 'permission_classes', None)
    if classes is None:
        return ', '.join(c.rsplit('.', 1)[-1] for c in settings.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'])
    return ', '.join(c.__name__ for c in classes)


ERRORS = {
    '400': 'данные не прошли проверку или недопустимый переход состояния',
    '403': 'нет входа в систему или не передан CSRF-токен',
    '404': 'объект не найден, удалён или принадлежит другому пользователю',
}


def build_openapi(routes):
    schemas, paths = {}, {}
    schemas['Error'] = {
        'type': 'object',
        'description': 'ошибка: {"поле": ["сообщение"]}, {"detail": "..."} или ["сообщение"]',
        'additionalProperties': True,
    }
    for route in routes:
        ser = route['serializer']
        name = schema_name(ser)
        response, request, _ = describe_serializer(ser)
        schemas[name] = response
        schemas[name + 'Input'] = request
        op = {
            'operationId': f"{route['view'].__name__}_{route['action']}",
            'summary': route['summary'],
            'tags': [route['url'].split('/')[2]],
            'x-handler': route['handler'],
            'responses': {},
        }
        params = []
        if route['detail']:
            params.append({'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}})
        if route['action'] == 'list':
            for pname, (ptype, pdesc) in getattr(route['view'], 'api_query_params', {}).items():
                params.append({'name': pname, 'in': 'query', 'required': False,
                               'description': pdesc, 'schema': {'type': ptype}})
        if params:
            op['parameters'] = params
        if route['has_body']:
            body = {'$ref': f'#/components/schemas/{name}Input'}
            if route['action'] == 'partial_update':
                body = {'allOf': [{'$ref': f'#/components/schemas/{name}Input'}],
                        'description': 'передаются только изменяемые поля'}
            op['requestBody'] = {'required': True, 'content': {'application/json': {'schema': body}}}
        code = SUCCESS.get(route['action'], '200')
        if code == '204':
            op['responses'][code] = {'description': 'выполнено, тело ответа пустое'}
        else:
            ref = {'$ref': f'#/components/schemas/{name}'}
            schema = {'type': 'array', 'items': ref} if route['is_list'] else ref
            op['responses'][code] = {'description': 'успешно',
                                     'content': {'application/json': {'schema': schema}}}
        codes = ['403']
        if route['method'] != 'get' or route['view'].__name__ == 'ReservationViewSet' and route['action'] == 'list':
            codes.insert(0, '400')
        if route['detail']:
            codes.append('404')
        for c in codes:
            op['responses'][c] = {'description': ERRORS[c],
                                  'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}}}
        if route['method'] != 'get':
            op['security'] = [{'sessionCookie': [], 'csrfToken': []}]
        paths.setdefault(route['url'], {})[route['method']] = op
    return {
        'openapi': '3.0.3',
        'info': {
            'title': 'SPO_SRS8 REST API',
            'version': release_version(),
            'description': 'Заявки и бронирование оборудования. Создано командой '
                           'python manage.py generate_api_docs - вручную не редактировать.',
        },
        'servers': [{'url': 'http://127.0.0.1:8000', 'description': 'локальный запуск'},
                    {'url': 'https://your-app.onrender.com', 'description': 'Render (подставьте свой домен)'}],
        'security': [{'sessionCookie': []}],
        'paths': paths,
        'components': {
            'schemas': dict(sorted(schemas.items())),
            'securitySchemes': {
                'sessionCookie': {'type': 'apiKey', 'in': 'cookie', 'name': 'sessionid',
                                  'description': 'сессия Django; вход через /accounts/login/'},
                'csrfToken': {'type': 'apiKey', 'in': 'header', 'name': 'X-CSRFToken',
                              'description': 'значение cookie csrftoken; нужно для POST, PUT, PATCH, DELETE'},
            },
        },
    }


def check_refs(spec):
    """Каждая ссылка $ref должна указывать на существующую схему."""
    text = json.dumps(spec)
    missing = {ref for ref in re.findall(r'#/components/schemas/(\w+)', text)
               if ref not in spec['components']['schemas']}
    if missing:
        raise CommandError(f'В схеме OpenAPI нет определений: {sorted(missing)}')


def render_reference(routes):
    lines = [
        '# Справочник REST API (создан автоматически)',
        '',
        'Файл создается автоматически командой',
        'python manage.py generate_api_docs из реальных маршрутов, сериализаторов и',
        'моделей проекта. Вручную не редактируется.',
        '',
        '## Маршруты',
        '',
        '| Метод | URL | Обработчик | Действие | Успех | Права доступа |',
        '|-------|-----|------------|----------|-------|---------------|',
    ]
    for r in routes:
        lines.append(f"| {r['method'].upper()} | {r['url']} | {r['handler']} | {r['summary']} | "
                     f"{SUCCESS.get(r['action'], '200')} | {permission_names(r['view'])} |")
    lines += ['', 'Все маршруты требуют входа в систему (сессия Django); изменяющие запросы - '
              'заголовок X-CSRFToken.', '', '## Параметры отбора', '',
              '| URL | Параметр | Тип | Описание |', '|-----|----------|-----|----------|']
    for r in routes:
        if r['action'] == 'list':
            for pname, (ptype, pdesc) in getattr(r['view'], 'api_query_params', {}).items():
                lines.append(f"| {r['url']} | {pname} | {ptype} | {pdesc} |")
    lines += ['', '## Поля данных', '']
    seen = []
    for r in routes:
        if r['serializer'] not in seen:
            seen.append(r['serializer'])
    for ser in seen:
        _, _, rows = describe_serializer(ser)
        model = getattr(ser.Meta, 'model', None)
        lines += [f'### {schema_name(ser)}' + (f' (модель {model.__name__})' if model else ''), '',
                  '| Поле | Тип | В запросе | Описание |', '|------|-----|-----------|----------|']
        lines += [f'| {n} | {t} | {req} | {d} |' for n, t, req, d in rows]
        lines.append('')
    return '\n'.join(lines)


class Command(BaseCommand):
    help = 'Создаёт docs/api-reference.md и docs/openapi.json по коду API'

    def add_arguments(self, parser):
        parser.add_argument('--check', action='store_true',
                            help='не писать файлы, а проверить их актуальность')

    def handle(self, *args, **options):
        routes = collect()
        spec = build_openapi(routes)
        check_refs(spec)
        outputs = {
            REFERENCE: render_reference(routes),
            OPENAPI: json.dumps(spec, ensure_ascii=False, indent=2) + '\n',
        }
        if options['check']:
            stale = [p.name for p, content in outputs.items()
                     if not p.is_file() or p.read_text(encoding='utf-8') != content]
            if stale:
                raise CommandError(f'устарели: {", ".join(stale)} - выполните '
                                   'python manage.py generate_api_docs')
            self.stdout.write(f'docs/api-reference.md и docs/openapi.json актуальны '
                              f'(маршрутов: {len(routes)}, схем данных: {len(spec["components"]["schemas"])})')
            return
        DOCS.mkdir(exist_ok=True)
        for path, content in outputs.items():
            path.write_text(content, encoding='utf-8')
            self.stdout.write(f'Записано: {path.relative_to(settings.BASE_DIR)}')
        self.stdout.write(f'Маршрутов: {len(routes)}, путей OpenAPI: {len(spec["paths"])}, '
                          f'схем данных: {len(spec["components"]["schemas"])}')
