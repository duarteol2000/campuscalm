from django import forms
from django.utils.translation import gettext_lazy as _

from planner.models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "due_date", "stress_level", "status"]
        labels = {
            "title": _("Titulo"),
            "description": _("Descricao"),
            "due_date": _("Data de entrega"),
            "stress_level": _("Nivel de estresse (1 a 5)"),
            "status": _("Status"),
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "due_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "stress_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }
