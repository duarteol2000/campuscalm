from django.contrib import admin

from billing.models import Plan, UserSubscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "is_active", "started_at")
    list_filter = ("is_active", "plan")
