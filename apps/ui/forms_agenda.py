from django import forms
from django.utils.translation import gettext_lazy as _

from agenda.models import CalendarEvent
from planner.models import Task


class CalendarEventForm(forms.ModelForm):
    class Meta:
        model = CalendarEvent
        fields = ["title", "event_type", "start_at", "end_at", "related_task", "notes"]
        labels = {
            "title": _("Titulo"),
            "event_type": _("Tipo"),
            "start_at": _("Inicio"),
            "end_at": _("Fim"),
            "related_task": _("Tarefa relacionada"),
            "notes": _("Observacoes"),
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "event_type": forms.Select(attrs={"class": "form-select"}),
            "start_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "related_task": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["start_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        if user is not None:
            self.fields["related_task"].queryset = Task.objects.filter(user=user).order_by("due_date")
        self.fields["related_task"].required = False
        self.fields["related_task"].empty_label = _("Estudos")
