from django import forms

from .models import Commitment, HelpRequest, Update


class HelpRequestForm(forms.ModelForm):
    class Meta:
        model = HelpRequest
        fields = ["title", "details", "size", "project", "repo_url"]
        widgets = {"details": forms.Textarea(attrs={"rows": 6}), "size": forms.RadioSelect}
        help_texts = {
            "title": "Exemple : « Mes WebSockets coupent derrière Nginx »",
            "details": "Ce que tu as essayé, ce que tu attends, ce qui se passe à la place.",
            "size": "Sois honnête : c'est ce qui permet aux autres de s'engager en connaissance de cause.",
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = user.projects.all()
        self.fields["project"].empty_label = "Aucun projet du mur"


class CommitmentForm(forms.ModelForm):
    understood = forms.BooleanField(
        label="J'ai lu la demande et je comprends de quoi il s'agit.",
        error_messages={"required": "Prends le temps de lire la demande avant de t'engager."},
    )
    available = forms.BooleanField(
        label="Ma situation me permet vraiment d'y consacrer ce temps.",
        error_messages={"required": "Ne t'engage que si tu as réellement ce temps."},
    )

    class Meta:
        model = Commitment
        fields = ["days", "message"]
        widgets = {"days": forms.RadioSelect}


class UpdateForm(forms.ModelForm):
    class Meta:
        model = Update
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3, "placeholder": "Où en est-on ?"})}
        labels = {"text": "Point d'avancement"}
