from django.contrib.auth import views as auth_views
from django.urls import path

from ui.forms import EmailAuthenticationForm
from ui.views import agenda_view, dashboard_view, messages_view, onboarding_view, semesters_view, tasks_view

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="ui/login.html",
            authentication_form=EmailAuthenticationForm,
        ),
        name="ui-login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="ui-logout"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="ui/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url="/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="ui/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="ui/password_reset_confirm.html",
            success_url="/reset/done/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="ui/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    path("", dashboard_view, name="ui-dashboard"),
    path("onboarding/", onboarding_view, name="ui-onboarding"),
    path("semesters/", semesters_view, name="ui-semesters"),
    path("tasks/", tasks_view, name="ui-tasks"),
    path("agenda/", agenda_view, name="ui-agenda"),
    path("messages/", messages_view, name="ui-messages"),
]
