from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import AcademicGroup, Course, Department, StudentProfile

from .models import ActivityEvent
from .utils import chart, kpi, percent, period_start, ru, step_for, time_ago, timeseries

METHODIST = 'Методист'
WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
ICONS = {'login': 'login', 'create': 'plus', 'update': 'pencil', 'delete': 'trash'}
Enrollment = StudentProfile.courses.through


class Filter:
    def __init__(self, name, label, choices, all_label='', default=None):
        self.name = name
        self.label = label
        self.choices = choices
        self.all_label = all_label
        self.default = default

    def options(self, department=None):
        items = self.choices() if callable(self.choices) else self.choices
        return [{'value': item[0], 'label': item[1]}
                for item in items if len(item) < 3 or not department or item[2] == department]

    def clean(self, raw, department=None):
        for option in self.options(department):
            if str(option['value']) == raw:
                return option['value']
        return self.default


def department_filter():
    return Filter('department', 'Факультет',
                  lambda: [(d.pk, d.name) for d in Department.objects.order_by('name')],
                  all_label='Все факультеты')


def group_filter():
    return Filter('group', 'Группа',
                  lambda: [(g.pk, g.name, g.department_id) for g in AcademicGroup.objects.order_by('name')],
                  all_label='Все группы')


def period_filter(choices, default):
    return Filter('period', 'Период', choices, default=default)


def departments_chart(queryset, series_name):
    items = list(queryset.order_by('pk'))
    return chart([d.name for d in items], (series_name, [d.n for d in items]))


class Dashboard:
    slug = ''
    title = ''
    description = ''
    icon = ''
    methodist_only = False
    filters = []
    table_title = ''
    columns = []

    def __init__(self, params=None):
        params = params or {}
        self.values = {}
        for f in self.filters:
            self.values[f.name] = f.clean(params.get(f.name), self.values.get('department'))

    @classmethod
    def allowed(cls, user):
        return not cls.methodist_only or user.is_superuser or user.groups.filter(name=METHODIST).exists()

    def filter_fields(self):
        return [{'filter': f, 'options': f.options(self.values.get('department')), 'current': self.values[f.name]}
                for f in self.filters]

    def build(self):
        raise NotImplementedError

    def summary(self):
        return []


class StudentsDashboard(Dashboard):
    slug = 'students'
    title = 'Контингент студентов'
    description = 'Численность студентов, наполняемость учебных групп и динамика регистрации на сайте.'
    icon = 'users'
    filters = [
        department_filter(),
        period_filter([(30, '30 дней'), (90, '90 дней'), (365, '12 месяцев'), (0, 'Всё время')], 365),
    ]
    table_title = 'Учебные группы'
    columns = [
        ('name', 'Группа'),
        ('department', 'Факультет'),
        ('students', 'Студентов'),
        ('avg_courses', 'Курсов на студента'),
        ('share', 'Доля факультета'),
    ]

    def build(self):
        department, days = self.values['department'], self.values['period']
        since = period_start(days)

        profiles = StudentProfile.objects.all()
        groups = AcademicGroup.objects.select_related('department')
        if department:
            profiles = profiles.filter(department_id=department)
            groups = groups.filter(department_id=department)

        total = profiles.count()
        joined = profiles.filter(user__date_joined__gte=since) if since else profiles
        with_courses = profiles.filter(courses__isnull=False).distinct().count()

        groups = list(groups.annotate(students_n=Count('students', distinct=True),
                                      enrollments_n=Count('students__courses'))
                      .order_by('-students_n', 'name'))
        in_groups = sum(g.students_n for g in groups)
        department_sizes = dict(Department.objects.annotate(n=Count('students')).values_list('pk', 'n'))

        step = step_for(days)
        labels, values = timeseries(joined, 'user__date_joined', since, step)

        return {
            'kpis': {
                'total': kpi(total, f'без учебной группы: {total - in_groups}'),
                'avg_group': kpi(round(in_groups / len(groups), 1) if groups else 0, f'учебных групп: {len(groups)}'),
                'with_courses': kpi(percent(with_courses, total),
                                    f'{with_courses} из {total} записаны хотя бы на один курс', '%'),
            },
            'charts': {
                'registrations': chart(labels, ('Новых студентов', values)),
                'by_department': departments_chart(Department.objects.annotate(n=Count('students')), 'Студентов'),
                'group_fill': chart([g.name for g in groups], ('Студентов', [g.students_n for g in groups])),
            },
            'rows': [{
                'name': g.name,
                'department': g.department.name,
                'students': g.students_n,
                'avg_courses': round(g.enrollments_n / g.students_n, 1) if g.students_n else 0,
                'share': percent(g.students_n, department_sizes.get(g.department_id, 0)),
            } for g in groups],
        }

    def summary(self):
        return [('студентов', StudentProfile.objects.count()), ('учебных групп', AcademicGroup.objects.count())]


class CoursesDashboard(Dashboard):
    slug = 'courses'
    title = 'Курсы и записи'
    description = 'Популярность курсов, учебная нагрузка студентов и распределение записей по факультетам.'
    icon = 'book'
    filters = [department_filter(), group_filter()]
    table_title = 'Курсы'
    columns = [
        ('title', 'Курс'),
        ('department', 'Факультет'),
        ('students', 'Студентов'),
        ('share', 'Охват студентов'),
    ]

    def build(self):
        department, group = self.values['department'], self.values['group']

        students = StudentProfile.objects.all()
        enrollments = Enrollment.objects.all()
        courses = Course.objects.select_related('department')
        if group:
            students = students.filter(academic_group_id=group)
            enrollments = enrollments.filter(studentprofile__academic_group_id=group)
        elif department:
            students = students.filter(department_id=department)
        if department:
            enrollments = enrollments.filter(course__department_id=department)
            courses = courses.filter(department_id=department)

        in_group = Q(students__academic_group_id=group) if group else Q()
        courses = list(courses.annotate(n=Count('students', filter=in_group)).order_by('-n', 'title'))
        students_n, enrollments_n = students.count(), enrollments.count()
        top = courses[0] if courses and courses[0].n else None

        own_courses = Q(courses__department_id=department) if department else Q()
        load = [0] * 6
        for n in students.annotate(n=Count('courses', filter=own_courses)).values_list('n', flat=True):
            load[min(n, 5)] += 1

        group_enrollments = Q(courses__students__academic_group_id=group) if group else Q()
        per_course = ru(round(enrollments_n / len(courses), 1)) if courses else 0

        return {
            'kpis': {
                'courses': kpi(len(courses), f'без студентов: {sum(1 for c in courses if not c.n)}'),
                'enrollments': kpi(enrollments_n, f'в среднем {per_course} на курс'),
                'load': kpi(round(enrollments_n / students_n, 1) if students_n else 0,
                            f'курсов на студента, студентов: {students_n}'),
                'top': kpi(top.title if top else '—', f'студентов: {top.n}' if top else 'нет записей'),
            },
            'charts': {
                'popularity': chart([c.title for c in courses[:10]], ('Студентов', [c.n for c in courses[:10]])),
                'by_department': departments_chart(
                    Department.objects.annotate(n=Count('courses__students', filter=group_enrollments)), 'Записей'),
                'load': chart(['0', '1', '2', '3', '4', '5+'], ('Студентов', load)),
            },
            'rows': [{
                'title': c.title,
                'department': c.department.name,
                'students': c.n,
                'share': percent(c.n, students_n),
            } for c in courses],
        }

    def summary(self):
        return [('курсов', Course.objects.count()), ('записей на курсы', Enrollment.objects.count())]


class ActivityDashboard(Dashboard):
    slug = 'activity'
    title = 'Активность на сайте'
    description = 'Входы пользователей и изменения учебных данных по журналу событий. Доступен методисту.'
    icon = 'activity'
    methodist_only = True
    filters = [
        period_filter([(7, '7 дней'), (30, '30 дней'), (90, '90 дней'), (365, '12 месяцев')], 30),
        Filter('action', 'Действие', [('login', 'Входы'), ('changes', 'Изменения данных')],
               all_label='Все действия'),
        Filter('role', 'Роль', [('student', 'Студенты'), ('methodist', 'Методисты')],
               all_label='Все пользователи'),
    ]

    def events(self, since):
        events = ActivityEvent.objects.filter(created_at__gte=since)
        if self.values['action'] == 'login':
            events = events.filter(action=ActivityEvent.Action.LOGIN)
        if self.values['action'] == 'changes':
            events = events.filter(action__in=ActivityEvent.CHANGES)
        if self.values['role'] == 'student':
            events = events.filter(user__student_profile__isnull=False)
        if self.values['role'] == 'methodist':
            events = events.filter(user__groups__name=METHODIST)
        return events

    def build(self):
        days = self.values['period']
        since = period_start(days)
        events = self.events(since).select_related('user')

        logins = events.filter(action=ActivityEvent.Action.LOGIN)
        changes = events.filter(action__in=ActivityEvent.CHANGES)
        active = events.exclude(user=None).values('user').distinct().count()
        users = User.objects.count()
        last = events.first()

        step = step_for(days)
        labels, login_values = timeseries(logins, 'created_at', since, step)
        _, change_values = timeseries(changes, 'created_at', since, step)

        heat = [[0] * 12 for _ in WEEKDAYS]
        for moment in events.values_list('created_at', flat=True):
            moment = timezone.localtime(moment)
            heat[moment.weekday()][moment.hour // 2] += 1

        by_section = dict(changes.values_list('section').annotate(n=Count('pk')))
        sections = [s for s in ActivityEvent.Section if s != ActivityEvent.Section.AUTH]

        top = (events.exclude(user=None)
               .values('user__username', 'user__last_name', 'user__first_name')
               .annotate(n=Count('pk')).order_by('-n', 'user__username')[:8])

        return {
            'kpis': {
                'logins': kpi(logins.count(), 'за выбранный период'),
                'active': kpi(active, f'{ru(percent(active, users))}% от {users} пользователей'),
                'changes': kpi(changes.count(), 'добавление, изменение, удаление'),
                'last': kpi(time_ago(last.created_at) if last else '—', last.user.username if last and last.user else ''),
            },
            'charts': {
                'timeline': chart(labels, ('Входы', login_values), ('Изменения данных', change_values)),
                'heatmap': {'labels': [], 'series': [
                    {'name': WEEKDAYS[d], 'data': [{'x': f'{h * 2:02d}:00', 'y': heat[d][h]} for h in range(12)]}
                    for d in reversed(range(7))]},
                'sections': chart([s.label for s in sections],
                                  ('Изменений', [by_section.get(s.value, 0) for s in sections])),
                'top_users': chart([f"{u['user__last_name']} {u['user__first_name']}".strip() or u['user__username']
                                    for u in top], ('Событий', [u['n'] for u in top])),
            },
            'feed': [{
                'user': e.user.username if e.user else 'система',
                'icon': ICONS[e.action],
                'text': e.get_action_display() if e.section == ActivityEvent.Section.AUTH
                else f'{e.get_action_display()} · {e.get_section_display().lower()}',
                'object': e.object_repr,
                'ago': time_ago(e.created_at),
            } for e in events[:12]],
        }

    def summary(self):
        recent = ActivityEvent.objects.filter(created_at__gte=period_start(30))
        return [('входов за 30 дней', recent.filter(action=ActivityEvent.Action.LOGIN).count()),
                ('изменений данных', recent.filter(action__in=ActivityEvent.CHANGES).count())]


DASHBOARDS = {d.slug: d for d in (StudentsDashboard, CoursesDashboard, ActivityDashboard)}


def available_dashboards(user):
    return [d for d in DASHBOARDS.values() if d.allowed(user)]
