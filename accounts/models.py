from django.contrib.auth.models import User
from django.db import models
from django.conf import settings


class Department(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='courses'
    )

    def __str__(self):
        return self.title


class AcademicGroup(models.Model):
    name = models.CharField(max_length=50)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='groups')

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile')

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students')

    academic_group = models.ForeignKey(
        AcademicGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students')

    courses = models.ManyToManyField(
        Course,
        blank=True,
        related_name='students')

    def __str__(self):
        return self.user.username

class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name

class Ticket(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        PROGRESS = "progress", "В работе"
        DONE = "done", "Выполнена"

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="tickets",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.NEW,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Equipment(models.Model):
    name = models.CharField(max_length=150, unique=True)
    total_q = models.PositiveIntegerField(default=0)
    available_q = models.PositiveIntegerField(default=0)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.available_q > self.total_q:
            raise ValidationError({
                'available_q': 'Доступное количество не может превышать общее'
            })

    def __str__(self):
        return self.name


class EquipmentReservation(models.Model):
    class Status(models.TextChoices):
        CREATED = 'created', 'Создано'
        ISSUED = 'issued', 'Выдано'
        RETURNED = 'returned', 'Возвращено'

    purpose = models.CharField(max_length=150)
    equipment = models.ForeignKey(
        Equipment, on_delete=models.PROTECT, related_name='reservations'
    )
    quantity = models.PositiveIntegerField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='equipment_reservations',
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.CREATED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.purpose


class ReservationEvent(models.Model):
    class Action(models.TextChoices):
        CREATED = 'created', 'Создание'
        EDITED = 'edited', 'Редактирование'
        ISSUED = 'issued', 'Выдача оборудования'
        RETURNED = 'returned', 'Возврат оборудования'
        DELETED = 'deleted', 'Удаление'

    reservation = models.ForeignKey(
        EquipmentReservation,
        on_delete=models.PROTECT,
        related_name='events',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='equipment_reservation_events',
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    details = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.reservation_id}: {self.get_action_display()}'