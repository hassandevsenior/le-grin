from django.conf import settings
from django.db import models
from django.urls import reverse

from core.models import Tech

MAX_STEPS = 7


class Path(models.Model):
    """« Je veux apprendre X » : la communauté trace la route, étape par étape."""

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="paths")
    title = models.CharField("ce que tu veux apprendre", max_length=80)
    context = models.TextField("d'où tu pars", max_length=600, blank=True)
    tech = models.ForeignKey(Tech, on_delete=models.SET_NULL, null=True, blank=True, related_name="paths")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("paths:detail", args=[self.pk])

    @property
    def is_full(self):
        return self.steps.count() >= MAX_STEPS


class Step(models.Model):
    path = models.ForeignKey(Path, on_delete=models.CASCADE, related_name="steps")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="steps")
    position = models.PositiveSmallIntegerField()
    title = models.CharField("l'étape", max_length=90)
    why = models.CharField("pourquoi à ce moment-là", max_length=200, blank=True)
    done_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="steps_done")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created"]

    def __str__(self):
        return self.title


class Explanation(models.Model):
    """Une explication résumée d'une étape. Le lien est facultatif : le résumé prime."""

    step = models.ForeignKey(Step, on_delete=models.CASCADE, related_name="explanations")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="explanations")
    summary = models.TextField("ton résumé", max_length=900)
    resource_url = models.URLField("ressource pour aller plus loin", blank=True)
    thanks = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="thanked")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created"]
