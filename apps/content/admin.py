from django.contrib import admin

from content.models import GuidedContent


@admin.register(GuidedContent)
class GuidedContentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "duration_minutes", "is_premium")
    list_filter = ("category", "is_premium")
