from django.contrib.auth import views as auth_views
from django.urls import path

from ui.forms import EmailAuthenticationForm
from ui.views import (
    activate_account_view,
    dashboard_view,
    first_access_view,
    home_view,
    onboarding_view,
    semesters_view,
    tasks_view,
)
from ui.views_academic import (
    assessment_create_view,
    assessment_delete_view,
    assessment_update_view,
    course_create_view,
    course_delete_view,
    course_detail_view,
    course_update_view,
    semester_create_view,
    semester_delete_view,
    semester_detail_view,
    semester_list_view,
    semester_update_view,
)
from ui.views_agenda import agenda_create_view, agenda_delete_view, agenda_list_view, agenda_update_view
from ui.views_messages import message_list_view
from ui.views_reminders import (
    reminder_create_view,
    reminder_delete_view,
    reminder_generate_view,
    reminder_list_view,
    reminder_update_view,
)
from ui.views_tasks import task_create_view, task_delete_view, task_detail_view, task_list_view, task_update_view

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="ui/login.html",
            authentication_form=EmailAuthenticationForm,
        ),
        name="ui-login",
    ),
    path("home/", home_view, name="ui-home"),
    path("primeiro-acesso/", first_access_view, name="ui-first-access"),
    path("ativar/<uidb64>/<token>/", activate_account_view, name="ui-activate-account"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="ui-logout"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="logout"),
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
    path("semestres/", semester_list_view, name="ui-semester-list"),
    path("semestres/novo/", semester_create_view, name="ui-semester-create"),
    path("semestres/<int:pk>/", semester_detail_view, name="ui-semester-detail"),
    path("semestres/<int:pk>/editar/", semester_update_view, name="ui-semester-edit"),
    path("semestres/<int:pk>/excluir/", semester_delete_view, name="ui-semester-delete"),
    path("semestres/<int:sem_id>/disciplinas/nova/", course_create_view, name="ui-course-create"),
    path("disciplinas/<int:pk>/", course_detail_view, name="ui-course-detail"),
    path("disciplinas/<int:pk>/editar/", course_update_view, name="ui-course-edit"),
    path("disciplinas/<int:pk>/excluir/", course_delete_view, name="ui-course-delete"),
    path("disciplinas/<int:course_id>/avaliacoes/nova/", assessment_create_view, name="ui-assessment-create"),
    path("avaliacoes/<int:pk>/editar/", assessment_update_view, name="ui-assessment-edit"),
    path("avaliacoes/<int:pk>/excluir/", assessment_delete_view, name="ui-assessment-delete"),
    path("tasks/", task_list_view, name="ui-tasks"),
    path("agenda/", agenda_list_view, name="ui-agenda-list"),
    path("messages/", message_list_view, name="ui-messages"),
    path("tarefas/", task_list_view, name="ui-task-list"),
    path("tarefas/nova/", task_create_view, name="ui-task-create"),
    path("tarefas/<int:pk>/", task_detail_view, name="ui-task-detail"),
    path("tarefas/<int:pk>/editar/", task_update_view, name="ui-task-edit"),
    path("tarefas/<int:pk>/excluir/", task_delete_view, name="ui-task-delete"),
    path("agenda/novo/", agenda_create_view, name="ui-agenda-create"),
    path("agenda/<int:pk>/editar/", agenda_update_view, name="ui-agenda-edit"),
    path("agenda/<int:pk>/excluir/", agenda_delete_view, name="ui-agenda-delete"),
    path("lembretes/", reminder_list_view, name="ui-reminder-list"),
    path("lembretes/gerar/", reminder_generate_view, name="ui-reminder-generate"),
    path("lembretes/novo/", reminder_create_view, name="ui-reminder-create"),
    path("lembretes/<int:pk>/editar/", reminder_update_view, name="ui-reminder-edit"),
    path("lembretes/<int:pk>/excluir/", reminder_delete_view, name="ui-reminder-delete"),
    path("mensagens/", message_list_view, name="ui-message-list"),
]
