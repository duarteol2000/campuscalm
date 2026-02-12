from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class EmailAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "inactive": _("Confirme seu e-mail para entrar."),
    }

    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "seu.email@universidade.edu"}),
    )
    password = forms.CharField(
        label=_("Senha"),
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Sua senha"}),
    )

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                user_model = get_user_model()
                user = user_model._default_manager.filter(email__iexact=username).first()
                if user and user.check_password(password) and not user.is_active:
                    raise forms.ValidationError(self.error_messages["inactive"], code="inactive")
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


# Bloco: Formulario de primeiro acesso
class FirstAccessForm(forms.Form):
    PLAN_FREE = "FREE"
    PLAN_PAID = "PAGO"
    PLAN_CHOICES = [
        (PLAN_FREE, _("Free")),
        (PLAN_PAID, _("Pago")),
    ]

    name = forms.CharField(label=_("Nome"), max_length=255, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(label=_("Email"), widget=forms.EmailInput(attrs={"class": "form-control"}))
    phone = forms.CharField(
        label=_("Telefone (WhatsApp)"),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    plan = forms.ChoiceField(
        label=_("Plano"),
        choices=PLAN_CHOICES,
        initial=PLAN_FREE,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    password1 = forms.CharField(
        label=_("Senha"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        min_length=6,
    )
    password2 = forms.CharField(
        label=_("Confirmar senha"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        min_length=6,
    )
    allow_email = forms.BooleanField(
        label=_("Receber email"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    allow_whatsapp = forms.BooleanField(
        label=_("Receber WhatsApp"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    allow_sms = forms.BooleanField(
        label=_("Receber SMS"),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            self.add_error("password2", _("As senhas nao conferem."))
        return data
