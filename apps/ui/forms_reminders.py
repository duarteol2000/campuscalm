from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from agenda.models import ReminderRule
from utils.constants import CHANNEL_EMAIL, CHANNEL_SMS, CHANNEL_WHATSAPP

CHANNEL_OPTIONS = [
    (CHANNEL_EMAIL, "Email"),
    (CHANNEL_WHATSAPP, "WhatsApp"),
    (CHANNEL_SMS, "SMS"),
]


class ReminderRuleForm(forms.ModelForm):
    channels = forms.MultipleChoiceField(
        choices=CHANNEL_OPTIONS,
        widget=forms.CheckboxSelectMultiple,
        label=_("Canais"),
        required=False,
    )

    class Meta:
        model = ReminderRule
        fields = ["target_type", "remind_before_minutes", "channels", "is_active"]
        labels = {
            "target_type": _("Tipo de alvo"),
            "remind_before_minutes": _("Minutos antes"),
            "is_active": _("Ativo"),
        }
        widgets = {
            "target_type": forms.Select(attrs={"class": "form-select"}),
            "remind_before_minutes": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.channels:
            self.fields["channels"].initial = self.instance.channels

    def clean_remind_before_minutes(self):
        minutes = self.cleaned_data.get("remind_before_minutes")
        if minutes is not None and minutes <= 0:
            raise ValidationError(_("Informe um valor maior que zero."))
        return minutes

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.channels = self.cleaned_data.get("channels", [])
        if commit:
            instance.save()
        return instance
