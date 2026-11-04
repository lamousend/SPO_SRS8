from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class ActivityEvent(models.Model):
    class Action(models.TextChoices):
        LOGIN = 'login', 'Вход в систему'
        CREATE = 'create', 'Добавление'
        UPDATE = 'update', 'Изменение'
        DELETE = 'delete', 'Удаление'

    class Section(models.TextChoices):
        AUTH = 'auth', 'Авторизация'
        DEPARTMENT = 'department', 'Факультеты'
        GROUP = 'group', 'Учебные группы'
        COURSE = 'course', 'Курсы'

    CHANGES = [Action.CREATE, Action.UPDATE, Action.DELETE]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='activity_events', verbose_name='Пользователь')
    action = models.CharField('Действие', max_length=10, choices=Action.choices)
    section = models.CharField('Раздел', max_length=20, choices=Section.choices)
    object_repr = models.CharField('Объект', max_length=255, blank=True)
    created_at = models.DateTimeField('Время', default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Событие'
        verbose_name_plural = 'Журнал событий'

    def __str__(self):
        return f'{self.get_action_display()}: {self.object_repr or self.user}'
