from django import forms

from core.models import Tech

from .models import Explanation, Path, Step


class PathForm(forms.ModelForm):
    tech_text = forms.CharField(label="Techno concernée", max_length=40, required=False)

    class Meta:
        model = Path
        fields = ["title", "context"]
        widgets = {"context": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "title": "Exemple : « Déployer une app Django sur un VPS »",
            "context": "Ce que tu sais déjà, ton système, ton objectif. Ça aide à tracer la bonne route.",
        }

    def save(self, author):
        path = super().save(commit=False)
        path.author = author
        techs = Tech.from_text(self.cleaned_data["tech_text"], limit=1)
        path.tech = techs[0] if techs else None
        path.save()
        return path


class StepForm(forms.ModelForm):
    class Meta:
        model = Step
        fields = ["title", "why"]


class ExplanationForm(forms.ModelForm):
    class Meta:
        model = Explanation
        fields = ["summary", "resource_url"]
        widgets = {"summary": forms.Textarea(attrs={"rows": 4})}

    def clean_summary(self):
        summary = self.cleaned_data["summary"].strip()
        if len(summary) < 40:
            raise forms.ValidationError(
                "Résume vraiment l'idée en quelques phrases : un lien seul n'aide pas à comprendre."
            )
        return summary
