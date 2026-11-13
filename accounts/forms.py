from django import forms
from django.contrib.auth.forms import UserCreationForm

from core.models import Tech

from .models import User

TECHS_HELP = "Sépare par des virgules : Django, Flutter, PostgreSQL"


class TechsMixin(forms.Form):
    """Ajoute un champ texte « technos » et sait l'enregistrer sur un objet qui a `.techs`."""

    techs_text = forms.CharField(label="Tes technos", required=False, max_length=200, help_text=TECHS_HELP)

    def init_techs(self):
        if self.instance.pk and not self.is_bound:
            self.fields["techs_text"].initial = ", ".join(t.name for t in self.instance.techs.all())

    def save_techs(self, instance):
        instance.techs.set(Tech.from_text(self.cleaned_data.get("techs_text", "")))


class SignupForm(TechsMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "level"]
        labels = {"username": "Pseudo"}
        help_texts = {"username": "Lettres, chiffres et @ . + - _"}

    field_order = ["username", "email", "level", "techs_text", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse.")
        return email

    def save(self, commit=True):
        user = super().save(commit)
        if commit:
            self.save_techs(user)
        return user


class ProfileForm(TechsMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["bio", "level", "city", "github"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_techs()

    def save(self, commit=True):
        user = super().save(commit)
        self.save_techs(user)
        return user
