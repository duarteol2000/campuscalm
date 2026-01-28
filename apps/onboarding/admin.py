from django.contrib import admin

from onboarding.models import UserSetupProgress


@admin.register(UserSetupProgress)
class UserSetupProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "has_profile", "has_active_semester", "has_at_least_one_course", "has_at_least_one_assessment", "has_reminder_rule")
