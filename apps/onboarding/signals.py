from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from accounts.models import User
from agenda.models import ReminderRule
from onboarding.services import refresh_user_progress
from semester.models import Assessment, Course, Semester


@receiver(post_save, sender=User)
def user_saved(sender, instance, **kwargs):
    refresh_user_progress(instance)


@receiver(post_save, sender=Semester)
@receiver(post_delete, sender=Semester)
def semester_changed(sender, instance, **kwargs):
    refresh_user_progress(instance.user)


@receiver(post_save, sender=Course)
@receiver(post_delete, sender=Course)
def course_changed(sender, instance, **kwargs):
    refresh_user_progress(instance.semester.user)


@receiver(post_save, sender=Assessment)
@receiver(post_delete, sender=Assessment)
def assessment_changed(sender, instance, **kwargs):
    refresh_user_progress(instance.course.semester.user)


@receiver(post_save, sender=ReminderRule)
@receiver(post_delete, sender=ReminderRule)
def reminder_changed(sender, instance, **kwargs):
    refresh_user_progress(instance.user)
