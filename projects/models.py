from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from core.models import Tech


class Project(models.Model):
    class Stage(models.TextChoices):
        IDEA = "idea", "Maquette"
        BUILDING = "building", "En construction"
        LIVE = "live", "En ligne"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField("nom du projet", max_length=60)
    slug = models.SlugField(max_length=70, unique=True)
    tagline = models.CharField("en une phrase", max_length=120, blank=True)
    description = models.TextField("l'histoire du projet", max_length=2000, blank=True)
    screenshot = models.ImageField("capture d'écran", upload_to="captures/%Y/%m/")
    live_url = models.URLField("lien du projet", blank=True)
    repo_url = models.URLField("dépôt Git", blank=True)
    stage = models.CharField("état", max_length=10, choices=Stage.choices, default=Stage.BUILDING)
    techs = models.ManyToManyField(Tech, blank=True, related_name="projects")
    applause = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="applauded")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("projects:detail", args=[self.slug])


class Pin(models.Model):
    """Un retour posé à un endroit précis de la capture (x et y en % de l'image)."""

    class Kind(models.TextChoices):
        LOVE = "love", "J'aime"
        IDEA = "idea", "Idée"
        BUG = "bug", "Souci"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="pins")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pins")
    x = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    y = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    kind = models.CharField(max_length=5, choices=Kind.choices, default=Kind.IDEA)
    text = models.CharField(max_length=280)
    resolved = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created"]

    def __str__(self):
        return f"{self.get_kind_display()} sur {self.project}"
