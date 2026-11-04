"""Тестовые данные для заявок (ПЗ 7) и бронирования оборудования (СРС 7).

Команда идемпотентна: повторный запуск не создаёт дубликатов и не
сбрасывает остатки оборудования, если они уже изменялись.
Пароли тестовых пользователей берутся из аргументов, в коде их нет.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Category, Equipment

CATEGORIES = ['Оборудование', 'Программное обеспечение', 'Сетевые сервисы']
EQUIPMENT = [('Проектор', 2), ('Ноутбук', 5), ('Графический планшет', 3)]


class Command(BaseCommand):
    help = 'Создаёт категории заявок, оборудование и двух тестовых пользователей'

    def add_arguments(self, parser):
        parser.add_argument('--password', required=True,
                            help='пароль для тестовых пользователей student1 и student2')

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']
        if len(password) < 8:
            raise CommandError('Пароль должен содержать не менее 8 символов')

        User = get_user_model()
        for name in CATEGORIES:
            _, created = Category.objects.get_or_create(name=name)
            self.stdout.write(f'категория {name}: {"создана" if created else "уже есть"}')

        for name, total in EQUIPMENT:
            _, created = Equipment.objects.get_or_create(
                name=name, defaults={'total_q': total, 'available_q': total})
            self.stdout.write(f'оборудование {name}: {"создано" if created else "уже есть"}')

        for username in ('student1', 'student2'):
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
            self.stdout.write(f'пользователь {username}: {"создан" if created else "уже есть"}')
