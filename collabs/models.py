from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class HelpRequest(models.Model):
    """Un « coup de main » : un blocage précis sur lequel on demande du renfort."""

    class Size(models.TextChoices):
        HOURS = "hours", "Quelques heures"
        DAYS = "days", "Quelques jours"
        WEEKS = "weeks", "Quelques semaines"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="help_requests")
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="help_requests", verbose_name="projet concerné",
    )
    title = models.CharField("le blocage en une ligne", max_length=100)
    details = models.TextField("ce qui se passe", max_length=2000)
    repo_url = models.URLField("dépôt Git", blank=True)
    size = models.CharField("taille du chantier", max_length=6, choices=Size.choices, default=Size.HOURS)
    is_open = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_open", "-created"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("collabs:detail", args=[self.pk])


class Commitment(models.Model):
    """L'engagement d'un membre sur un coup de main, pour une durée choisie."""

    DURATIONS = [(1, "24 heures"), (3, "3 jours"), (7, "1 semaine"), (14, "2 semaines"), (30, "1 mois")]

    class Status(models.TextChoices):
        ACTIVE = "active", "En cours"
        KEPT = "kept", "Tenu"
        RELEASED = "released", "Libéré"

    request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name="commitments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="commitments")
    days = models.PositiveSmallIntegerField("durée", choices=DURATIONS, default=3)
    message = models.CharField("un mot pour l'auteur", max_length=280, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    created = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField()

    class Meta:
        ordering = ["created"]
        constraints = [models.UniqueConstraint(fields=["request", "user"], name="one_commitment_per_member")]

    def save(self, *args, **kwargs):
        if not self.ends_at:
            self.ends_at = timezone.now() + timedelta(days=self.days)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Un engagement en cours dont la date est passée n'engage plus personne."""
        return self.status == self.Status.ACTIVE and self.ends_at <= timezone.now()

    @property
    def is_running(self):
        return self.status == self.Status.ACTIVE and not self.is_expired

    @property
    def progress(self):
        """Part du temps écoulé, de 0 à 100, pour la jauge."""
        total = (self.ends_at - self.created).total_seconds() or 1
        elapsed = (timezone.now() - self.created).total_seconds()
        return max(0, min(100, round(100 * elapsed / total)))


class Update(models.Model):
    """Un point d'avancement dans le fil d'un coup de main."""

    request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name="updates")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(max_length=1500)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created"]
