from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Tech(models.Model):
    """Une technologie (Django, Flutter...). Sert de lien entre membres, projets et parcours."""

    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @classmethod
    def from_text(cls, text, limit=8):
        """Transforme "Django, vue.js , django" en liste de Tech sans doublon."""
        techs, seen = [], set()
        for raw in text.replace(";", ",").split(","):
            name = " ".join(raw.split())[:40]
            slug = slugify(name.replace("+", " plus ").replace("#", " sharp ").replace(".", " "))
            if not slug or slug in seen:
                continue
            seen.add(slug)
            tech, _ = cls.objects.get_or_create(slug=slug, defaults={"name": name})
            techs.append(tech)
            if len(techs) == limit:
                break
        return techs


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    text = models.CharField(max_length=200)
    url = models.CharField(max_length=200)
    read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=["recipient", "read"])]

    def __str__(self):
        return self.text


def notify(recipient, actor, text, url):
    """Prévient `recipient`, sauf s'il est lui-même à l'origine de l'action."""
    if recipient.pk != actor.pk:
        Notification.objects.create(recipient=recipient, text=text[:200], url=url)
