from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from accounts.models import AcademicGroup, Course, Department

from .middleware import current_user
from .models import ActivityEvent

SECTIONS = {
    Department: ActivityEvent.Section.DEPARTMENT,
    AcademicGroup: ActivityEvent.Section.GROUP,
    Course: ActivityEvent.Section.COURSE,
}


@receiver(user_logged_in)
def log_login(sender, user, **kwargs):
    ActivityEvent.objects.create(user=user, action=ActivityEvent.Action.LOGIN,
                                 section=ActivityEvent.Section.AUTH)


def log_change(instance, action):
    user = current_user.get()
    ActivityEvent.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        section=SECTIONS[type(instance)],
        object_repr=str(instance),
    )


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    if sender in SECTIONS:
        log_change(instance, ActivityEvent.Action.CREATE if created else ActivityEvent.Action.UPDATE)


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if sender in SECTIONS:
        log_change(instance, ActivityEvent.Action.DELETE)
