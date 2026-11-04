"""Автотесты REST API: заявки (ПЗ 7) и бронирование оборудования (СРС 7).

Запуск: python manage.py test accounts
Тесты используют временную БД и не затрагивают рабочие данные.
"""
from unittest import mock

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from .models import (Category, Equipment, EquipmentReservation,
                     ReservationEvent, Ticket)

User = get_user_model()


class ApiBase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('student1', password='pass-12345')
        self.other = User.objects.create_user('student2', password='pass-12345')
        self.category = Category.objects.create(name='Оборудование')
        self.projector = Equipment.objects.create(
            name='Проектор', total_q=2, available_q=2)
        self.laptop = Equipment.objects.create(
            name='Ноутбук', total_q=5, available_q=5)
        self.client.force_login(self.user)


class HealthAndAuthTests(ApiBase):
    def test_healthz_is_public(self):
        anon = APIClient()
        response = anon.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_api_requires_login(self):
        anon = APIClient()
        for url in ('/api/tickets/', '/api/categories/',
                    '/api/equipment/', '/api/reservations/'):
            self.assertIn(anon.get(url).status_code, (401, 403), url)


class TicketApiTests(ApiBase):
    def create_ticket(self, title='Не работает принтер'):
        return self.client.post('/api/tickets/', {
            'title': title, 'category': self.category.pk}, format='json')

    def test_create_ticket_sets_owner_and_new_status(self):
        response = self.create_ticket()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body['status'], 'new')
        self.assertEqual(body['category_name'], 'Оборудование')
        self.assertEqual(Ticket.objects.get(pk=body['id']).owner, self.user)

    def test_short_title_rejected(self):
        response = self.client.post('/api/tickets/', {
            'title': 'abc', 'category': self.category.pk}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('title', response.json())

    def test_status_transitions(self):
        pk = self.create_ticket().json()['id']
        url = f'/api/tickets/{pk}/'
        self.assertEqual(
            self.client.patch(url, {'status': 'progress'}, format='json').status_code, 200)
        self.assertEqual(
            self.client.patch(url, {'status': 'done'}, format='json').status_code, 200)
        response = self.client.patch(url, {'status': 'new'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Ticket.objects.get(pk=pk).status, 'done')

    def test_skipping_status_rejected(self):
        pk = self.create_ticket().json()['id']
        response = self.client.patch(
            f'/api/tickets/{pk}/', {'status': 'done'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_foreign_ticket_is_404(self):
        pk = self.create_ticket().json()['id']
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f'/api/tickets/{pk}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/tickets/{pk}/').status_code, 404)
        self.assertEqual(self.client.get('/api/tickets/').json(), [])

    def test_status_filter_and_delete(self):
        pk = self.create_ticket().json()['id']
        self.create_ticket('Установить Python')
        self.client.patch(f'/api/tickets/{pk}/', {'status': 'progress'}, format='json')
        listed = self.client.get('/api/tickets/?status=progress').json()
        self.assertEqual([t['id'] for t in listed], [pk])
        self.assertEqual(self.client.delete(f'/api/tickets/{pk}/').status_code, 204)
        self.assertFalse(Ticket.objects.filter(pk=pk).exists())


class ReservationApiTests(ApiBase):
    def create(self, quantity=2, equipment=None, purpose='Практическая работа'):
        return self.client.post('/api/reservations/', {
            'purpose': purpose,
            'equipment': (equipment or self.projector).pk,
            'quantity': quantity}, format='json')

    def test_create_adds_created_event(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body['status'], 'created')
        events = self.client.get(f"/api/reservations/{body['id']}/history/").json()
        self.assertEqual([e['action'] for e in events], ['created'])

    def test_validation_errors(self):
        self.assertEqual(self.create(quantity=0).status_code, 400)
        self.assertEqual(self.create(purpose='abc').status_code, 400)
        response = self.client.post('/api/reservations/', {
            'purpose': 'Практическая работа', 'equipment': self.projector.pk,
            'quantity': 1, 'status': 'issued'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_issue_and_return_cycle(self):
        pk = self.create().json()['id']
        issued = self.client.post(f'/api/reservations/{pk}/issue/')
        self.assertEqual(issued.status_code, 200)
        self.assertEqual(issued.json()['status'], 'issued')
        self.projector.refresh_from_db()
        self.assertEqual(self.projector.available_q, 0)

        returned = self.client.post(f'/api/reservations/{pk}/return_equipment/')
        self.assertEqual(returned.status_code, 200)
        self.assertEqual(returned.json()['status'], 'returned')
        self.projector.refresh_from_db()
        self.assertEqual(self.projector.available_q, 2)

        actions = [e['action'] for e in
                   self.client.get(f'/api/reservations/{pk}/history/').json()]
        self.assertEqual(actions, ['created', 'issued', 'returned'])

    def test_repeated_issue_forbidden(self):
        pk = self.create().json()['id']
        self.client.post(f'/api/reservations/{pk}/issue/')
        response = self.client.post(f'/api/reservations/{pk}/issue/')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ReservationEvent.objects.filter(reservation_id=pk).count(), 2)

    def test_return_before_issue_forbidden(self):
        pk = self.create().json()['id']
        response = self.client.post(f'/api/reservations/{pk}/return_equipment/')
        self.assertEqual(response.status_code, 400)

    def test_issue_more_than_available_forbidden(self):
        pk = self.create(quantity=6, equipment=self.laptop).json()['id']
        response = self.client.post(f'/api/reservations/{pk}/issue/')
        self.assertEqual(response.status_code, 400)
        self.laptop.refresh_from_db()
        self.assertEqual(self.laptop.available_q, 5)
        self.assertEqual(EquipmentReservation.objects.get(pk=pk).status, 'created')

    def test_issue_rolls_back_when_event_fails(self):
        pk = self.create().json()['id']
        with mock.patch('accounts.reservation_services.ReservationEvent.objects.create',
                        side_effect=RuntimeError('сбой записи события')):
            with self.assertRaises(RuntimeError):
                self.client.post(f'/api/reservations/{pk}/issue/')
        self.projector.refresh_from_db()
        self.assertEqual(self.projector.available_q, 2)
        self.assertEqual(EquipmentReservation.objects.get(pk=pk).status, 'created')
        self.assertEqual(ReservationEvent.objects.filter(reservation_id=pk).count(), 1)

    def test_foreign_reservation_is_404(self):
        pk = self.create().json()['id']
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f'/api/reservations/{pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/reservations/{pk}/issue/').status_code, 404)

    def test_soft_delete_keeps_history(self):
        pk = self.create().json()['id']
        self.assertEqual(self.client.delete(f'/api/reservations/{pk}/').status_code, 204)
        self.assertEqual(self.client.get(f'/api/reservations/{pk}/').status_code, 404)
        reservation = EquipmentReservation.objects.get(pk=pk)
        self.assertIsNotNone(reservation.deleted_at)
        self.assertEqual(reservation.events.count(), 2)

    def test_issued_reservation_cannot_be_edited_or_deleted(self):
        pk = self.create().json()['id']
        self.client.post(f'/api/reservations/{pk}/issue/')
        self.assertEqual(self.client.patch(
            f'/api/reservations/{pk}/', {'quantity': 1}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/reservations/{pk}/').status_code, 400)

    def test_two_filters(self):
        a = self.create(quantity=1).json()['id']
        self.create(quantity=1, equipment=self.laptop)
        self.client.post(f'/api/reservations/{a}/issue/')
        listed = self.client.get(
            f'/api/reservations/?status=issued&equipment={self.projector.pk}').json()
        self.assertEqual([r['id'] for r in listed], [a])
        self.assertEqual(
            self.client.get('/api/reservations/?equipment=abc').status_code, 400)


class OpenApiContractTests(ApiBase):
    """Ответы API совпадают со сгенерированной схемой docs/openapi.json.

    Схема создаётся из кода командой generate_api_docs; этот тест проверяет,
    что описание не только актуально, но и верно: реальные ответы содержат
    ровно документированные поля нужных типов и документированные коды.
    """
    TYPES = {'integer': int, 'string': str, 'boolean': bool}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import json
        from pathlib import Path
        from django.conf import settings
        path = Path(settings.BASE_DIR) / 'docs' / 'openapi.json'
        cls.spec = json.loads(path.read_text(encoding='utf-8'))

    def resolve(self, schema):
        if '$ref' in schema:
            return self.spec['components']['schemas'][schema['$ref'].rsplit('/', 1)[-1]]
        return schema

    def assert_matches(self, url, method, response):
        operation = self.spec['paths'][url][method]
        code = str(response.status_code)
        self.assertIn(code, operation['responses'], f'{method.upper()} {url}: код {code} не описан')
        content = operation['responses'][code].get('content')
        if not content or code >= '400':
            return
        schema = content['application/json']['schema']
        data = response.json()
        if schema.get('type') == 'array':
            self.assertIsInstance(data, list)
            self.assertTrue(data, f'{url}: для проверки нужен непустой список')
            schema, items = self.resolve(schema['items']), data
        else:
            schema, items = self.resolve(schema), [data]
        for item in items:
            self.assertEqual(set(item), set(schema['properties']), f'{method.upper()} {url}: поля')
            for name, prop in schema['properties'].items():
                if item[name] is None:
                    continue
                if 'enum' in prop:
                    self.assertIn(item[name], prop['enum'], f'{url}: {name}')
                elif prop['type'] in self.TYPES:
                    self.assertIsInstance(item[name], self.TYPES[prop['type']], f'{url}: {name}')

    def test_responses_match_schema(self):
        ticket = self.client.post('/api/tickets/', {'title': 'Проверка схемы', 'category': self.category.pk},
                                  format='json')
        self.assert_matches('/api/tickets/', 'post', ticket)
        tid = ticket.json()['id']
        self.assert_matches('/api/tickets/', 'get', self.client.get('/api/tickets/'))
        self.assert_matches('/api/tickets/{id}/', 'patch',
                            self.client.patch(f'/api/tickets/{tid}/', {'status': 'progress'}, format='json'))
        self.assert_matches('/api/tickets/{id}/', 'patch',
                            self.client.patch(f'/api/tickets/{tid}/', {'status': 'new'}, format='json'))
        self.assert_matches('/api/categories/', 'get', self.client.get('/api/categories/'))
        self.assert_matches('/api/equipment/', 'get', self.client.get('/api/equipment/'))
        res = self.client.post('/api/reservations/', {'purpose': 'Проверка схемы', 'equipment': self.projector.pk,
                                                      'quantity': 1}, format='json')
        self.assert_matches('/api/reservations/', 'post', res)
        rid = res.json()['id']
        self.assert_matches('/api/reservations/', 'get', self.client.get('/api/reservations/?status=created'))
        self.assert_matches('/api/reservations/', 'get', self.client.get('/api/reservations/?equipment=abc'))
        self.assert_matches('/api/reservations/{id}/issue/', 'post',
                            self.client.post(f'/api/reservations/{rid}/issue/'))
        self.assert_matches('/api/reservations/{id}/issue/', 'post',
                            self.client.post(f'/api/reservations/{rid}/issue/'))
        self.assert_matches('/api/reservations/{id}/history/', 'get',
                            self.client.get(f'/api/reservations/{rid}/history/'))
        self.assert_matches('/api/reservations/{id}/return_equipment/', 'post',
                            self.client.post(f'/api/reservations/{rid}/return_equipment/'))
        self.assert_matches('/api/reservations/{id}/', 'get', self.client.get('/api/reservations/9999/'))
        self.assert_matches('/api/tickets/{id}/', 'delete', self.client.delete(f'/api/tickets/{tid}/'))

    def test_every_documented_route_exists(self):
        from accounts.management.commands.generate_api_docs import collect
        actual = {(r['url'], r['method']) for r in collect()}
        documented = {(url, m) for url, ops in self.spec['paths'].items() for m in ops}
        self.assertEqual(actual, documented)
