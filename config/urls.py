from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("ui.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/auth/", include("accounts.urls")),
    path("api/billing/", include("billing.urls")),
    path("api/mood/", include("mood.urls")),
    path("api/pomodoro/", include("pomodoro.urls")),
    path("api/planner/", include("planner.urls")),
    path("api/agenda/", include("agenda.urls")),
    path("api/semester/", include("semester.urls")),
    path("api/content/", include("content.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/access/", include("access_requests.urls")),
    path("api/onboarding/", include("onboarding.urls")),
    path("api/analytics/", include("analytics.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
