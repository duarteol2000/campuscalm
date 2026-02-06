from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from agenda.models import CalendarEvent
from notifications.services.reminder_queue import create_notifications_for_event
from ui.forms_agenda import CalendarEventForm


@login_required(login_url="/login/")
def agenda_list_view(request):
    events = CalendarEvent.objects.filter(user=request.user).order_by("start_at")
    return render(
        request,
        "ui/agenda/agenda_list.html",
        {
            "events": events,
            "now": timezone.now(),
        },
    )


@login_required(login_url="/login/")
def agenda_create_view(request):
    if request.method == "POST":
        form = CalendarEventForm(request.POST, user=request.user)
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user
            event.save()
            # Bloco: Criacao de lembretes para evento
            create_notifications_for_event(request.user, event)
            messages.success(request, _("Evento criado com sucesso."))
            return redirect("ui-agenda-list")
    else:
        form = CalendarEventForm(user=request.user)
    return render(request, "ui/agenda/agenda_form.html", {"form": form, "mode": "create"})


@login_required(login_url="/login/")
def agenda_update_view(request, pk: int):
    event = get_object_or_404(CalendarEvent, pk=pk, user=request.user)
    if request.method == "POST":
        form = CalendarEventForm(request.POST, instance=event, user=request.user)
        if form.is_valid():
            event = form.save()
            # Bloco: Atualizacao de lembretes para evento
            create_notifications_for_event(request.user, event)
            messages.success(request, _("Evento atualizado com sucesso."))
            return redirect("ui-agenda-list")
    else:
        form = CalendarEventForm(instance=event, user=request.user)
    return render(request, "ui/agenda/agenda_form.html", {"form": form, "mode": "edit", "event": event})


@login_required(login_url="/login/")
def agenda_delete_view(request, pk: int):
    event = get_object_or_404(CalendarEvent, pk=pk, user=request.user)
    if request.method == "POST":
        event.delete()
        messages.success(request, _("Evento excluido com sucesso."))
        return redirect("ui-agenda-list")
    return render(request, "ui/agenda/agenda_confirm_delete.html", {"event": event})
