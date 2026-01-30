from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from semester.models import Assessment, Course, Semester


class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ["name", "start_date", "end_date", "status"]
        labels = {
            "name": _("Nome do semestre"),
            "start_date": _("Data de inicio"),
            "end_date": _("Data de termino"),
            "status": _("Status"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "teacher", "credits", "passing_grade", "status", "final_grade", "notes"]
        labels = {
            "title": _("Nome da disciplina"),
            "teacher": _("Professor"),
            "credits": _("Creditos"),
            "passing_grade": _("Nota minima"),
            "status": _("Status"),
            "final_grade": _("Nota final"),
            "notes": _("Anotacoes"),
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "teacher": forms.TextInput(attrs={"class": "form-control"}),
            "credits": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "passing_grade": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": 0}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "final_grade": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": 0}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def clean_passing_grade(self):
        passing_grade = self.cleaned_data.get("passing_grade")
        if passing_grade is not None and passing_grade <= 0:
            raise ValidationError(_("A nota minima deve ser maior que zero."))
        return passing_grade


class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ["title", "score", "max_score", "weight", "date"]
        labels = {
            "title": _("Titulo"),
            "score": _("Nota obtida"),
            "max_score": _("Nota maxima"),
            "weight": _("Peso"),
            "date": _("Data"),
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "score": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": 0}),
            "max_score": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": 0}),
            "weight": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": 0}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get("score")
        max_score = cleaned_data.get("max_score")
        weight = cleaned_data.get("weight")
        if score is not None and max_score is not None and score > max_score:
            raise ValidationError(_("A nota obtida nao pode ser maior que a nota maxima."))
        if weight is not None and weight < 0:
            raise ValidationError(_("O peso deve ser maior ou igual a zero."))
        return cleaned_data
