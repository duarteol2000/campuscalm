from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import UserProfile
from agenda.models import CalendarEvent, ReminderRule
from billing.models import Plan, UserSubscription
from brain.models import InteracaoAluno
from notifications.models import NotificationQueue
from onboarding.services import refresh_user_progress
from planner.models import Task
from pomodoro.models import PomodoroSession
from semester.models import Course, Semester
from brain.services import build_dashboard_insights, maybe_send_absence_email
from utils.academic_progress import (
    calculate_course_average,
    calculate_needed_to_pass,
    calculate_progress_percent,
    update_course_status,
)
from utils.constants import (
    EVENT_TYPE_CHOICES,
    CHANNEL_IN_APP,
    SEMESTER_ACTIVE,
    SEMESTER_FINISHED,
    TASK_DOING,
    TASK_DONE,
    TASK_TODO,
    PLAN_LITE,
    PLAN_PRO,
)
from utils.gating import STEPS, compute_status
from ui.forms import FirstAccessForm, ProfileSettingsForm

STEP_LABELS = {
    "STEP_1_PROFILE": _("Perfil"),
    "STEP_2_SEMESTER": _("Semestre"),
    "STEP_3_COURSES": _("Disciplinas"),
    "STEP_4_ASSESSMENTS": _("Avaliacoes"),
    "STEP_5_REMINDERS": _("Lembretes"),
    "STEP_6_DASHBOARD": _("Dashboard"),
}


def home_view(request):
    return render(request, "ui/home.html")


def _build_activation_url(request, uidb64, token):
    activate_path = reverse("ui-activate-account", kwargs={"uidb64": uidb64, "token": token})
    site_base_url = (settings.SITE_BASE_URL or "").strip().rstrip("/")
    if site_base_url:
        return f"{site_base_url}{activate_path}"
    return request.build_absolute_uri(activate_path)


def _send_activation_email(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activation_url = _build_activation_url(request, uidb64, token)
    context = {"user": user, "activation_url": activation_url}

    subject = _("Ative sua conta no CampusCalm")
    text_body = render_to_string("accounts/email/activate_account.txt", context)
    html_body = render_to_string("accounts/email/activate_account.html", context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)


def _build_steps(progress):
    current_step, missing_steps, required_actions = compute_status(progress)
    steps = []
    for step, _field, message in STEPS:
        label = STEP_LABELS.get(step, step)
        is_missing = step in missing_steps
        steps.append(
            {
                "code": step,
                "label": label,
                "missing": is_missing,
                "message": message if is_missing else _("Concluido"),
            }
        )
    total_steps = len(steps)
    completed_steps = total_steps - len(missing_steps)
    progress_percent = int((completed_steps / total_steps) * 100) if total_steps else 0
    return {
        "current_step": current_step,
        "missing_steps": missing_steps,
        "required_actions": required_actions,
        "steps": steps,
        "is_complete": len(missing_steps) == 0,
        "total_steps": total_steps,
        "completed_steps": completed_steps,
        "progress_percent": progress_percent,
    }


# Bloco: Primeiro acesso / Criar conta
def first_access_view(request):
    user_model = get_user_model()
    if request.method == "POST":
        form = FirstAccessForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            if user_model.objects.filter(email=email).exists():
                form.add_error("email", _("Ja existe um usuario com este email."))
                return render(request, "ui/first_access.html", {"form": form})

            user = user_model.objects.create_user(
                email=email,
                name=form.cleaned_data["name"],
                phone_number=form.cleaned_data.get("phone", ""),
                password=form.cleaned_data["password1"],
                is_active=False,
            )

            profile = UserProfile.objects.get_or_create(user=user)[0]
            profile.phone = form.cleaned_data.get("phone", "")
            profile.plan = form.cleaned_data["plan"]
            profile.allow_email = form.cleaned_data.get("allow_email", True)
            profile.allow_whatsapp = form.cleaned_data.get("allow_whatsapp", True)
            profile.allow_sms = form.cleaned_data.get("allow_sms", False)
            profile.consent_at = timezone.now()
            profile.save()

            plan_code = PLAN_PRO if profile.plan == UserProfile.PLAN_PAID else PLAN_LITE
            plan = Plan.objects.filter(code=plan_code, is_active=True).first()
            if plan:
                UserSubscription.objects.get_or_create(user=user, defaults={"plan": plan})

            _send_activation_email(request, user)
            messages.success(request, _("Enviamos um link de ativacao para seu e-mail."))
            return redirect("ui-login")
    else:
        form = FirstAccessForm()
    return render(request, "ui/first_access.html", {"form": form})


def activate_account_view(request, uidb64, token):
    user_model = get_user_model()
    user = None
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = user_model.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, user_model.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
            messages.success(request, _("Conta ativada com sucesso. Agora voce pode entrar."))
        else:
            messages.info(request, _("Sua conta ja esta ativada."))
    else:
        messages.error(request, _("Link de ativacao invalido ou expirado."))
    return redirect("ui-login")


@login_required(login_url="/login/")
def profile_view(request):
    profile = UserProfile.objects.get_or_create(user=request.user)[0]

    if request.method == "POST":
        form = ProfileSettingsForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Perfil atualizado com sucesso."))
            return redirect("ui-profile")
        messages.error(request, _("Nao foi possivel salvar seu perfil. Verifique os campos e tente novamente."))
    else:
        form = ProfileSettingsForm(instance=profile)

    return render(
        request,
        "ui/profile.html",
        {
            "form": form,
        },
    )


@login_required(login_url="/login/")
def dashboard_view(request):
    user = request.user
    progress = refresh_user_progress(user)
    onboarding_status = _build_steps(progress)

    session_key = "ui_dashboard_filters"
    if request.GET.get("clear") == "1":
        request.session.pop(session_key, None)
        return redirect(request.path)
    if "q" in request.GET:
        search_query = request.GET.get("q", "").strip()
        request.session[session_key] = {"q": search_query}
    else:
        search_query = request.session.get(session_key, {}).get("q", "")

    insights_data = build_dashboard_insights(user)
    today = timezone.localdate()
    next_week = today + timedelta(days=7)
    upcoming_tasks = Task.objects.filter(user=user, due_date__gte=today, due_date__lte=next_week).order_by("due_date")
    upcoming_events = CalendarEvent.objects.filter(
        user=user, start_at__date__gte=today, start_at__date__lte=next_week
    ).order_by("start_at")
    if search_query:
        upcoming_tasks = upcoming_tasks.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
        upcoming_events = upcoming_events.filter(title__icontains=search_query)

    tasks = Task.objects.filter(user=user)
    courses = Course.objects.filter(semester__user=user).select_related("semester").order_by("title")
    course_progress = []
    for course in courses:
        course_progress.append(
            {
                "title": course.title,
                "semester": course.semester.name,
                "current_average": calculate_course_average(course),
                "passing_grade": course.passing_grade,
                "progress_percent": int(calculate_progress_percent(course)),
            }
        )
    dashboard_data = {
        "tasks": {
            "todo": tasks.filter(status=TASK_TODO).count(),
            "doing": tasks.filter(status=TASK_DOING).count(),
            "done": tasks.filter(status=TASK_DONE).count(),
        },
        "message_andamento": insights_data["message_andamento"],
        "mood_weekly_total": insights_data["mood_weekly_total"],
        "mood_most_common": insights_data["mood_most_common"],
        "focus_minutes_week": insights_data["focus_minutes_week"],
        "stress_avg_week": insights_data["stress_avg_week"],
        "upcoming_tasks": upcoming_tasks[:5],
        "upcoming_events": upcoming_events[:5],
        "upcoming_count": insights_data["upcoming_count"],
        "course_progress": course_progress[:5],
    }

    if insights_data.get("absence_alert_active"):
        dashboard_url = request.build_absolute_uri(reverse("ui-dashboard"))
        maybe_send_absence_email(user=user, dashboard_url=dashboard_url)

    return render(
        request,
        "ui/dashboard.html",
        {
            "onboarding_status": onboarding_status,
            "dashboard_data": dashboard_data,
            "search_query": search_query,
        },
    )


@login_required(login_url="/login/")
def insights_detail_view(request):
    insight_type = (request.GET.get("type") or "").strip().lower()
    valid_types = {"mood", "stress", "focus", "upcoming"}
    if insight_type not in valid_types:
        return HttpResponseBadRequest("invalid insight type")

    user = request.user
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    context = {}

    if insight_type == "mood":
        interactions = (
            InteracaoAluno.objects.filter(user=user, created_at__gte=week_ago, categoria_detectada__isnull=False)
            .select_related("categoria_detectada")
            .order_by("-created_at")
        )
        counts = {}
        for interaction in interactions:
            slug = interaction.categoria_detectada.slug
            counts[slug] = counts.get(slug, 0) + 1
        mood_rows = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        context = {
            "rows": mood_rows,
            "total": len(interactions),
        }
        template_name = "ui/partials/insight_mood_detail.html"
    elif insight_type == "stress":
        interactions = InteracaoAluno.objects.filter(user=user, created_at__gte=week_ago)
        total_interacoes = interactions.count()
        stress_count = interactions.filter(categoria_detectada__slug="stress").count()
        stress_avg_week = build_dashboard_insights(user)["stress_avg_week"]
        context = {
            "stress_count": stress_count,
            "total_interacoes": total_interacoes,
            "stress_avg_week": stress_avg_week,
        }
        template_name = "ui/partials/insight_stress_detail.html"
    elif insight_type == "focus":
        sessions = PomodoroSession.objects.filter(user=user, started_at__gte=week_ago).order_by("-started_at")
        total_minutes = sum(session.focus_minutes for session in sessions)
        context = {
            "sessions": sessions[:20],
            "total_minutes": total_minutes,
        }
        template_name = "ui/partials/insight_focus_detail.html"
    else:
        today = timezone.localdate()
        next_week = today + timedelta(days=7)
        tasks = (
            Task.objects.filter(user=user, due_date__gte=today, due_date__lte=next_week)
            .exclude(status=TASK_DONE)
            .order_by("due_date")
        )
        events = CalendarEvent.objects.filter(
            user=user,
            start_at__date__gte=today,
            start_at__date__lte=next_week,
        ).order_by("start_at")
        upcoming_items = []
        for task in tasks:
            upcoming_items.append(
                {
                    "kind": "task",
                    "title": task.title,
                    "when": timezone.make_aware(datetime.combine(task.due_date, time.min)),
                }
            )
        for event in events:
            upcoming_items.append(
                {
                    "kind": "event",
                    "title": event.title,
                    "when": event.start_at,
                }
            )
        upcoming_items.sort(key=lambda item: item["when"])
        context = {
            "items": upcoming_items,
            "total": len(upcoming_items),
        }
        template_name = "ui/partials/insight_upcoming_detail.html"

    return render(request, template_name, context)


@login_required(login_url="/login/")
def onboarding_view(request):
    user = request.user
    progress = refresh_user_progress(user)
    onboarding_status = _build_steps(progress)
    return render(
        request,
        "ui/onboarding.html",
        {
            "current_step": onboarding_status["current_step"],
            "missing_steps": onboarding_status["missing_steps"],
            "required_actions": onboarding_status["required_actions"],
            "steps": onboarding_status["steps"],
        },
    )


@login_required(login_url="/login/")
def semesters_view(request):
    user = request.user
    session_key = "ui_semesters_filters"
    if request.GET.get("clear") == "1":
        request.session.pop(session_key, None)
        return redirect(request.path)
    if any(key in request.GET for key in ("status", "course", "teacher")):
        status_filter = request.GET.get("status", "")
        course_query = request.GET.get("course", "").strip()
        teacher_query = request.GET.get("teacher", "").strip()
        request.session[session_key] = {
            "status": status_filter,
            "course": course_query,
            "teacher": teacher_query,
        }
    else:
        saved = request.session.get(session_key, {})
        status_filter = saved.get("status", "")
        course_query = saved.get("course", "")
        teacher_query = saved.get("teacher", "")
    semesters = Semester.objects.filter(user=user)
    if status_filter in {SEMESTER_ACTIVE, SEMESTER_FINISHED}:
        semesters = semesters.filter(status=status_filter)
    semesters = semesters.order_by("-start_date")
    semester_cards = []
    for semester in semesters.prefetch_related("courses__assessments"):
        courses_data = []
        for course in semester.courses.all():
            if course_query and course_query.lower() not in course.title.lower():
                continue
            if teacher_query and teacher_query.lower() not in (course.teacher or "").lower():
                continue
            current_average = calculate_course_average(course)
            progress_percent = calculate_progress_percent(course)
            progress_value = float(progress_percent)
            progress_display = f"{progress_value:.2f}"
            needed_to_pass = calculate_needed_to_pass(course)
            previous_status = course.status
            update_course_status(course, semester_status=semester.status)
            if course.status != previous_status:
                course.save(update_fields=["status"])
            courses_data.append(
                {
                    "title": course.title,
                    "teacher": course.teacher,
                    "status": course.status,
                    "passing_grade": course.passing_grade,
                    "current_average": current_average,
                    "progress_percent": progress_display,
                    "progress_percent_css": progress_display,
                    "needed_to_pass": needed_to_pass,
                }
            )
        if (course_query or teacher_query) and not courses_data:
            continue
        semester_cards.append(
            {
                "name": semester.name,
                "start_date": semester.start_date,
                "end_date": semester.end_date,
                "status": semester.status,
                "courses": courses_data,
            }
        )

    return render(
        request,
        "ui/semesters.html",
        {
            "semesters": semester_cards,
            "status_filter": status_filter,
            "course_query": course_query,
            "teacher_query": teacher_query,
        },
    )


@login_required(login_url="/login/")
def tasks_view(request):
    user = request.user
    session_key = "ui_tasks_filters"
    if request.GET.get("clear") == "1":
        request.session.pop(session_key, None)
        return redirect(request.path)
    if any(key in request.GET for key in ("status", "due", "q", "stress")):
        status_filter = request.GET.get("status", "")
        due_filter = request.GET.get("due", "")
        search_query = request.GET.get("q", "").strip()
        stress_filter = request.GET.get("stress", "")
        request.session[session_key] = {
            "status": status_filter,
            "due": due_filter,
            "q": search_query,
            "stress": stress_filter,
        }
    else:
        saved = request.session.get(session_key, {})
        status_filter = saved.get("status", "")
        due_filter = saved.get("due", "")
        search_query = saved.get("q", "")
        stress_filter = saved.get("stress", "")
    tasks = Task.objects.filter(user=user)
    if status_filter in {TASK_TODO, TASK_DOING, TASK_DONE}:
        tasks = tasks.filter(status=status_filter)
    today = timezone.localdate()
    if due_filter == "overdue":
        tasks = tasks.filter(due_date__lt=today)
    elif due_filter == "today":
        tasks = tasks.filter(due_date=today)
    elif due_filter == "week":
        tasks = tasks.filter(due_date__gte=today, due_date__lte=today + timedelta(days=7))
    elif due_filter == "month":
        tasks = tasks.filter(due_date__gte=today, due_date__lte=today + timedelta(days=30))
    if search_query:
        tasks = tasks.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
    if stress_filter in {"1", "2", "3", "4", "5"}:
        tasks = tasks.filter(stress_level=int(stress_filter))
    tasks = tasks.order_by("due_date")
    return render(
        request,
        "ui/tasks.html",
        {
            "tasks": tasks,
            "status_filter": status_filter,
            "due_filter": due_filter,
            "search_query": search_query,
            "stress_filter": stress_filter,
        },
    )


@login_required(login_url="/login/")
def agenda_view(request):
    user = request.user
    today = timezone.localdate()
    session_key = "ui_agenda_filters"
    if request.GET.get("clear") == "1":
        request.session.pop(session_key, None)
        return redirect(request.path)
    if any(key in request.GET for key in ("range", "q", "type")):
        range_days = request.GET.get("range", "30")
        if range_days not in {"7", "15", "30", "60", "90"}:
            range_days = "30"
        search_query = request.GET.get("q", "").strip()
        type_filter = request.GET.get("type", "")
        request.session[session_key] = {
            "range": range_days,
            "q": search_query,
            "type": type_filter,
        }
    else:
        saved = request.session.get(session_key, {})
        range_days = saved.get("range", "30")
        search_query = saved.get("q", "")
        type_filter = saved.get("type", "")
    next_month = today + timedelta(days=int(range_days))
    events = CalendarEvent.objects.filter(
        user=user, start_at__date__gte=today, start_at__date__lte=next_month
    ).order_by("start_at")
    if search_query:
        events = events.filter(title__icontains=search_query)
    event_type_values = [value for value, _label in EVENT_TYPE_CHOICES]
    if type_filter in event_type_values:
        events = events.filter(event_type=type_filter)
    reminder_rules = ReminderRule.objects.filter(user=user, is_active=True)
    return render(
        request,
        "ui/agenda.html",
        {
            "events": events,
            "reminder_rules": reminder_rules,
            "range_days": range_days,
            "search_query": search_query,
            "type_filter": type_filter,
            "event_type_choices": EVENT_TYPE_CHOICES,
        },
    )


@login_required(login_url="/login/")
def messages_view(request):
    user = request.user
    notifications = NotificationQueue.objects.filter(user=user, channel=CHANNEL_IN_APP).order_by("-scheduled_for")
    return render(
        request,
        "ui/messages.html",
        {
            "notifications": notifications,
        },
    )
