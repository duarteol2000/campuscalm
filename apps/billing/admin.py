from django.contrib import admin

from billing.models import Institution, InstitutionSubscription, Plan, UserSubscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "price", "max_students", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("institution_code", "razao_social", "nome_fantasia", "ativa", "is_pilot", "cidade", "estado", "created_at")
    list_filter = ("ativa", "is_pilot", "estado")
    search_fields = ("razao_social", "nome_fantasia", "institution_code", "slug")
    prepopulated_fields = {"slug": ("razao_social",)}


@admin.register(InstitutionSubscription)
class InstitutionSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("institution", "plan", "status", "start_date", "end_date", "is_trial", "created_at")
    list_filter = ("status", "is_trial", "plan")
    search_fields = ("institution__institution_code", "institution__razao_social")
    date_hierarchy = "start_date"


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "is_active", "started_at")
    list_filter = ("is_active", "plan")
