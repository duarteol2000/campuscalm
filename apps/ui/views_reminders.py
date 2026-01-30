from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from agenda.models import ReminderRule
from ui.forms_reminders import ReminderRuleForm


@login_required(login_url="/login/")
def reminder_list_view(request):
    reminders = ReminderRule.objects.filter(user=request.user).order_by("-is_active", "remind_before_minutes")
    return render(request, "ui/reminders/reminder_list.html", {"reminders": reminders})


@login_required(login_url="/login/")
def reminder_create_view(request):
    if request.method == "POST":
        form = ReminderRuleForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.user = request.user
            reminder.save()
            messages.success(request, _("Regra de lembrete criada com sucesso."))
            return redirect("ui-reminder-list")
    else:
        form = ReminderRuleForm()
    return render(request, "ui/reminders/reminder_form.html", {"form": form, "mode": "create"})


@login_required(login_url="/login/")
def reminder_update_view(request, pk: int):
    reminder = get_object_or_404(ReminderRule, pk=pk, user=request.user)
    if request.method == "POST":
        form = ReminderRuleForm(request.POST, instance=reminder)
        if form.is_valid():
            form.save()
            messages.success(request, _("Regra de lembrete atualizada com sucesso."))
            return redirect("ui-reminder-list")
    else:
        form = ReminderRuleForm(instance=reminder)
    return render(
        request,
        "ui/reminders/reminder_form.html",
        {"form": form, "mode": "edit", "reminder": reminder},
    )


@login_required(login_url="/login/")
def reminder_delete_view(request, pk: int):
    reminder = get_object_or_404(ReminderRule, pk=pk, user=request.user)
    if request.method == "POST":
        reminder.delete()
        messages.success(request, _("Regra de lembrete excluida com sucesso."))
        return redirect("ui-reminder-list")
    return render(request, "ui/reminders/reminder_confirm_delete.html", {"reminder": reminder})
