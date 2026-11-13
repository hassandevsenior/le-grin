from django import forms
from django.utils.text import slugify

from accounts.forms import TechsMixin

from .images import process_screenshot
from .models import Pin, Project


def unique_slug(title):
    base = slugify(title)[:60] or "projet"
    slug, number = base, 2
    while Project.objects.filter(slug=slug).exists():
        slug = f"{base}-{number}"
        number += 1
    return slug


class ProjectForm(TechsMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = ["screenshot", "title", "tagline", "live_url", "repo_url", "stage", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "screenshot": forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
        }
        help_texts = {
            "tagline": "Ce que ça fait, pour qui.",
            "repo_url": "S'il est public.",
            "description": "Pourquoi tu l'as construit, ce qui a été dur, ce qui reste à faire.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["techs_text"].label = "Construit avec"
        self.init_techs()

    def clean_screenshot(self):
        upload = self.cleaned_data.get("screenshot")
        # À la modification sans nouveau fichier, Django renvoie le fichier déjà stocké.
        if upload and hasattr(upload, "content_type"):
            return process_screenshot(upload)
        return upload

    def clean(self):
        data = super().clean()
        if not data.get("live_url") and not data.get("repo_url"):
            raise forms.ValidationError("Donne au moins un lien : le projet en ligne ou son dépôt Git.")
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
