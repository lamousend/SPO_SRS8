import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ActivityEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("login", "Вход в систему"),
                            ("create", "Добавление"),
                            ("update", "Изменение"),
                            ("delete", "Удаление"),
                        ],
                        max_length=10,
                        verbose_name="Действие",
                    ),
                ),
                (
                    "section",
                    models.CharField(
                        choices=[
                            ("auth", "Авторизация"),
                            ("department", "Факультеты"),
                            ("group", "Учебные группы"),
                            ("course", "Курсы"),
                        ],
                        max_length=20,
                        verbose_name="Раздел",
                    ),
                ),
                (
                    "object_repr",
                    models.CharField(blank=True, max_length=255, verbose_name="Объект"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                        verbose_name="Время",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="activity_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Событие",
                "verbose_name_plural": "Журнал событий",
                "ordering": ["-created_at"],
            },
        ),
    ]
