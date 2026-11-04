from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AcademicGroup, Course, Department, StudentProfile

from .models import ActivityEvent


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.it = Department.objects.create(name='ИТ')
        cls.math = Department.objects.create(name='Математика')
        group = AcademicGroup.objects.create(name='М3О-236БВ-25', department=cls.it)
        web = Course.objects.create(title='Веб', department=cls.it)
        db = Course.objects.create(title='Базы данных', department=cls.it)
        Course.objects.create(title='Анализ', department=cls.math)

        cls.methodist = User.objects.create_user('methodist', password='pass')
        cls.methodist.groups.add(Group.objects.create(name='Методист'))
        cls.student = User.objects.create_user('student', password='pass')
        StudentProfile.objects.create(user=cls.student, department=cls.it, academic_group=group).courses.set([web, db])

    def setUp(self):
        ActivityEvent.objects.all().delete()

    def data(self, slug, **params):
        return self.client.get(reverse('dashboard_page', args=[slug]), params).context['data']

    def test_access(self):
        self.assertEqual(self.client.get(reverse('dashboard_page', args=['students'])).status_code, 302)
        self.client.login(username='student', password='pass')
        self.assertEqual(self.client.get(reverse('dashboard_page', args=['students'])).status_code, 200)
        self.assertEqual(self.client.get(reverse('dashboard_page', args=['activity'])).status_code, 403)
        self.assertEqual(self.client.get(reverse('dashboard_page', args=['unknown'])).status_code, 404)

    def test_students_follow_database(self):
        self.client.login(username='methodist', password='pass')
        self.assertEqual(self.data('students')['kpis']['total']['value'], 1)
        StudentProfile.objects.create(user=User.objects.create_user('new'), department=self.math)
        self.assertEqual(self.data('students')['kpis']['total']['value'], 2)
        self.assertEqual(self.data('students', department=self.math.pk)['kpis']['total']['value'], 1)

    def test_new_course_appears(self):
        self.client.login(username='methodist', password='pass')
        self.assertEqual(self.data('courses')['kpis']['enrollments']['value'], 2)
        Course.objects.create(title='Новый курс', department=self.it)
        data = self.data('courses', department=self.it.pk)
        self.assertEqual(data['kpis']['courses']['hint'], 'без студентов: 1')
        self.assertIn('Новый курс', [row['title'] for row in data['rows']])

    def test_wrong_filter_is_ignored(self):
        self.client.login(username='methodist', password='pass')
        self.assertEqual(self.data('courses', department='abc')['kpis']['courses']['value'], 3)

    def test_export_csv(self):
        self.client.login(username='methodist', password='pass')
        response = self.client.get(reverse('dashboard_export', args=['courses']))
        self.assertIn('Базы данных', response.content.decode('utf-8-sig'))

    def test_activity_log(self):
        self.client.login(username='methodist', password='pass')
        self.client.post(reverse('course_create'), {'title': 'Django', 'department': self.it.pk})
        event = ActivityEvent.objects.get(action='create')
        self.assertEqual((event.user, event.section, event.object_repr), (self.methodist, 'course', 'Django'))
        self.assertTrue(ActivityEvent.objects.filter(user=self.methodist, action='login').exists())
        self.assertEqual(self.data('activity', action='changes')['feed'][0]['object'], 'Django')
