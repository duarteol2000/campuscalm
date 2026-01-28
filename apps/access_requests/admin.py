from django.contrib import admin

from access_requests.models import AccessRequest, AITriageLog


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ("requester_email", "requester_type", "status", "recommended_plan", "decided_plan")
    list_filter = ("status", "requester_type")
    search_fields = ("requester_email", "requester_name")


@admin.register(AITriageLog)
class AITriageLogAdmin(admin.ModelAdmin):
    list_display = ("access_request", "model_name", "created_at")
