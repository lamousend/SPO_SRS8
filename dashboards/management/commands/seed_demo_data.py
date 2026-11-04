import random
from datetime import datetime, timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import AcademicGroup, Course, Department, StudentProfile
from dashboards.models import ActivityEvent

DEMO_EMAIL = '@students.uch.local'
PASSWORD = 'student236'

STRUCTURE = {
    'Информационные технологии': (
        ['М3О-236БВ-25', 'М3О-237БВ-25', 'М3О-234БВ-25', 'М3О-136БВ-26', 'М3О-335БВ-24'],
        ['Веб-программирование', 'Базы данных', 'Программирование на Python', 'Разработка веб-приложений',
         'Компьютерные сети', 'Алгоритмы и структуры данных'],
    ),
    'Прикладная математика': (
        ['М3О-111БВ-25', 'М3О-112БВ-25', 'М3О-116БВ-26'],
        ['Математическое моделирование', 'Теория вероятностей', 'Численные методы', 'Математическая статистика'],
    ),
    'Управление инновациями': (
        ['М3О-317БВ-25', 'М3О-318БВ-24'],
        ['Управление проектами', 'Инновационный менеджмент', 'Экономика предприятия'],
    ),
    'Системы управления': (
        ['М3О-321БВ-25', 'М3О-422БВ-23'],
        ['Теория автоматического управления', 'Моделирование систем управления', 'Микропроцессорные системы'],
    ),
}

LAST_NAMES = ['Иванов', 'Смирнов', 'Кузнецов', 'Попов', 'Васильев', 'Петров', 'Соколов', 'Михайлов', 'Новиков',
              'Морозов', 'Волков', 'Алексеев', 'Лебедев', 'Семёнов', 'Егоров', 'Павлов', 'Козлов', 'Степанов',
              'Николаев', 'Орлов', 'Андреев', 'Макаров', 'Никитин', 'Захаров', 'Зайцев', 'Борисов', 'Романов',
              'Сергеев', 'Фролов', 'Беляев', 'Тарасов', 'Белов', 'Комаров', 'Киселёв', 'Ильин', 'Гусев', 'Титов']
MALE_NAMES = ['Александр', 'Дмитрий', 'Максим', 'Иван', 'Артём', 'Никита', 'Михаил', 'Егор', 'Андрей', 'Кирилл',
              'Илья', 'Матвей', 'Роман', 'Тимофей', 'Даниил']
FEMALE_NAMES = ['Анастасия', 'Мария', 'Дарья', 'Анна', 'Елизавета', 'Полина', 'Виктория', 'Екатерина', 'Софья',
                'Алиса', 'Ксения', 'Александра', 'Валерия', 'Варвара', 'Вероника']
ELECTIVES = ['Факультатив: анализ данных', 'Спецкурс: Django', 'Практикум по SQL', 'Основы UX']
HOUR_WEIGHTS = [5, 2, 1, 1, 1, 3, 10, 35, 70, 100, 100, 90, 75, 85, 80, 70, 60, 65, 80, 90, 85, 60, 35, 15]

LATIN = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                 ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's',
                  't', 'u', 'f', 'h', 'ts', 'ch', 'sh', 'sch', '', 'y', '', 'e', 'yu', 'ya']))


def latin(text):
    return ''.join(LATIN.get(ch, ch) for ch in text.lower())


class Command(BaseCommand):
    help = 'Наполняет базу тестовыми студентами, записями на курсы и журналом событий'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='удалить ранее созданные тестовые данные')

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        self.random = random.Random(236)
        self.now = timezone.now()

        if reset:
            User.objects.filter(email__endswith=DEMO_EMAIL).delete()
            ActivityEvent.objects.all().delete()
        if User.objects.filter(email__endswith=DEMO_EMAIL).exists():
            self.stdout.write('Тестовые данные уже добавлены. Пересоздать: seed_demo_data --reset')
            return

        groups, courses = self.create_structure()
        students = self.create_students(groups, courses)
        self.create_events(students, groups, courses)

        self.stdout.write(self.style.SUCCESS(
            f'Факультетов: {Department.objects.count()}, групп: {AcademicGroup.objects.count()}, '
            f'курсов: {Course.objects.count()}, студентов: {StudentProfile.objects.count()}, '
            f'событий: {ActivityEvent.objects.count()}'))

    def create_structure(self):
        existing = set(Department.objects.values_list('name', flat=True))
        Department.objects.bulk_create([Department(name=n) for n in STRUCTURE if n not in existing])
        departments = {d.name: d for d in Department.objects.filter(name__in=STRUCTURE)}

        existing_groups = set(AcademicGroup.objects.values_list('name', flat=True))
        existing_courses = set(Course.objects.values_list('title', flat=True))
        for name, (group_names, course_titles) in STRUCTURE.items():
            AcademicGroup.objects.bulk_create([AcademicGroup(name=g, department=departments[name])
                                               for g in group_names if g not in existing_groups])
            Course.objects.bulk_create([Course(title=c, department=departments[name])
                                        for c in course_titles if c not in existing_courses])

        group_names = [g for names, _ in STRUCTURE.values() for g in names]
        groups = sorted(AcademicGroup.objects.filter(name__in=group_names), key=lambda g: group_names.index(g.name))
        courses = {d.pk: list(d.courses.all()) for d in departments.values()}
        return groups, courses

    def moment(self, start, end=None, recent=True):
        end = end or self.now
        while True:
            share = self.random.random() ** (0.7 if recent else 1)
            moment = end - (end - start) * (1 - share)
            local = timezone.localtime(moment)
            weight = HOUR_WEIGHTS[local.hour] * (1 if local.weekday() < 5 else 0.45)
            if self.random.random() * 100 < weight:
                return moment.replace(microsecond=0)

    def joined(self, group):
        start = timezone.make_aware(datetime(max(2000 + int(group.name[-2:]), 2025), 8, 25, 10))
        if self.random.random() < 0.7:
            return start + timedelta(days=self.random.uniform(0, 24))
        return min(self.moment(start, recent=False), self.now - timedelta(hours=1))

    def create_students(self, groups, courses):
        password = make_password(PASSWORD)
        used = set(User.objects.values_list('username', flat=True))
        students = []

        for group in groups:
            size = 6 if group.name.endswith('-23') else self.random.randint(9, 24)
            for _ in range(size):
                female = self.random.random() < 0.45
                first = self.random.choice(FEMALE_NAMES if female else MALE_NAMES)
                last = self.random.choice(LAST_NAMES) + ('а' if female else '')
                base = f'{latin(last)}.{latin(first)[0]}'
                username, number = base, 1
                while username in used:
                    number += 1
                    username = f'{base}{number}'
                used.add(username)

                user = User.objects.create(username=username, first_name=first, last_name=last,
                                           email=username + DEMO_EMAIL, password=password,
                                           date_joined=self.joined(group))
                profile = StudentProfile.objects.create(
                    user=user, department=group.department,
                    academic_group=None if self.random.random() < 0.05 else group)

                own = courses[group.department_id]
                count = self.random.choices(range(6), weights=[4, 14, 30, 30, 15, 7])[0]
                chosen = self.random.sample(own, min(count, len(own)))
                if self.random.random() < 0.15:
                    chosen.append(self.random.choice([c for d, items in courses.items()
                                                      if d != group.department_id for c in items]))
                profile.courses.set(chosen)
                students.append((user, self.random.choice([0.3, 0.6, 1.0, 1.5])))
        return students

    def create_events(self, students, groups, courses):
        horizon = self.now - timedelta(days=200)
        events = []

        def add(user, action, section, start, end=None, name='', recent=True):
            moment = self.moment(start, end, recent)
            events.append(ActivityEvent(user=user, action=action, section=section, object_repr=name,
                                        created_at=moment))
            return moment

        for user, activity in students:
            start = max(user.date_joined, horizon)
            end = self.now if self.random.random() > 0.3 else start + (self.now - start) * self.random.uniform(0.1, 0.8)
            count = max(1, int((end - start).days / 9 * activity * self.random.uniform(0.5, 1.2)))
            logins = [add(user, ActivityEvent.Action.LOGIN, ActivityEvent.Section.AUTH, start, end) for _ in range(count)]
            User.objects.filter(pk=user.pk).update(last_login=max(logins))

        methodists = Group.objects.get_or_create(name='Методист')[0].user_set.all()
        staff = list(methodists) + list(User.objects.filter(is_superuser=True))
        for user in staff:
            for _ in range(self.random.randint(45, 70)):
                add(user, ActivityEvent.Action.LOGIN, ActivityEvent.Section.AUTH, horizon)
        for user in User.objects.filter(username='student1'):
            for _ in range(14):
                add(user, ActivityEvent.Action.LOGIN, ActivityEvent.Section.AUTH, self.now - timedelta(days=60))

        objects = ([(ActivityEvent.Section.DEPARTMENT, d.name) for d in Department.objects.all()]
                   + [(ActivityEvent.Section.GROUP, g.name) for g in groups]
                   + [(ActivityEvent.Section.COURSE, c.title) for items in courses.values() for c in items])
        editors = staff or [None]
        for section, name in objects:
            year = 2026 if name.endswith('-26') else 2025
            add(self.random.choice(editors), ActivityEvent.Action.CREATE, section,
                timezone.make_aware(datetime(year, 8, 20)), name=name, recent=False)
        for _ in range(110):
            action = self.random.choices(ActivityEvent.CHANGES, weights=[15, 75, 10])[0]
            section, name = self.random.choice(objects)
            if action != ActivityEvent.Action.UPDATE:
                section, name = ActivityEvent.Section.COURSE, self.random.choice(ELECTIVES)
            add(self.random.choice(editors), action, section, horizon, name=name)

        ActivityEvent.objects.bulk_create(events)
