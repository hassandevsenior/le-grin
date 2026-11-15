from django import forms
from django.utils.text import slugify

from accounts.forms import TechsMixin

from .images import process_screenshot, render_terminal
from .models import Pin, Project


def unique_slug(title):
    base = slugify(title)[:60] or "projet"
    slug, number = base, 2
    while Project.objects.filter(slug=slug).exists():
        slug = f"{base}-{number}"
        number += 1
    return slug


class ProjectForm(TechsMixin, forms.ModelForm):
    terminal = forms.CharField(
        label="Pas d'interface graphique ?",
        required=False,
        max_length=4000,
        widget=forms.Textarea(attrs={"rows": 8, "spellcheck": "false", "class": "mono",
                                     "placeholder": "$ sugu sync --depuis hier\n✔ 128 ventes synchronisées en 2,4 s"}),
        help_text="Une API, une bibliothèque, un outil en ligne de commande ? Colle une sortie de terminal "
                  "ou un extrait de code : on en fait l'image du projet, et les retours s'y posent comme sur une capture.",
    )

    class Meta:
        model = Project
        fields = ["screenshot", "title", "tagline", "live_url", "repo_url", "stage", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "screenshot": forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
        }
        help_texts = {
            "tagline": "Ce que ça fait, pour qui.",
            "live_url": "Le site, l'app sur le store, la page du paquet…",
            "repo_url": "S'il est public.",
            "description": "Pourquoi tu l'as construit, ce qui a été dur, ce qui reste à faire.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["techs_text"].label = "Construit avec"
        self.fields["screenshot"].required = False  # une sortie de terminal peut la remplacer (voir clean)
        self.init_techs()

    def clean_screenshot(self):
        upload = self.cleaned_data.get("screenshot")
        # À la modification sans nouveau fichier, Django renvoie le fichier déjà stocké.
        if upload and hasattr(upload, "content_type"):
            return process_screenshot(upload)
        return upload

    def clean(self):
        data = super().clean()
        terminal = (data.get("terminal") or "").strip("\n")
        has_new_file = hasattr(self.files.get("screenshot"), "content_type")
        if terminal.strip() and not has_new_file:
            data["screenshot"] = render_terminal(terminal)
        elif not data.get("screenshot") and not self.errors.get("screenshot"):
            self.add_error(
                "screenshot",
                "Ajoute une capture d'écran. Pas d'interface ? Colle plutôt une sortie de terminal juste en dessous.",
            )
        return data

    def save(self, owner=None):
        project = super().save(commit=False)
        if owner:
            project.owner = owner
            project.slug = unique_slug(project.title)
        project.save()
        self.save_techs(project)
        return project


class PinForm(forms.ModelForm):
    class Meta:
        model = Pin
        fields = ["x", "y", "kind", "text"]

    def clean_text(self):
        text = " ".join(self.cleaned_data["text"].split())
        if len(text) < 3:
            raise forms.ValidationError("Écris au moins quelques mots.")
        return text
