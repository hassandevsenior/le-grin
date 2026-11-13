from django.conf import settings
from django.db import models
from django.urls import reverse


class Debate(models.Model):
    """La question du moment. Une seule est mise en avant à la fois."""

    question = models.CharField(max_length=160)
    slug = models.SlugField(max_length=80, unique=True)
    intro = models.CharField(max_length=240, blank=True)
    featured = models.BooleanField("à la une", default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-featured", "-created"]

    def __str__(self):
        return self.question

    def get_absolute_url(self):
        return reverse("debates:detail", args=[self.slug])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.featured:
            Debate.objects.exclude(pk=self.pk).filter(featured=True).update(featured=False)

    def tally(self):
        """Répartition des avis : [{"key", "label", "count", "percent"}, ...]."""
        counts = dict(self.stances.values_list("choice").annotate(n=models.Count("id")))
        total = sum(counts.values())
        return [
            {
                "key": key,
                "label": label,
                "count": counts.get(key, 0),
                "percent": round(100 * counts.get(key, 0) / total) if total else 0,
            }
            for key, label in Stance.Choice.choices
        ]


class Stance(models.Model):
    class Choice(models.TextChoices):
        YES = "yes", "Oui"
        MIXED = "mixed", "Ça dépend"
        NO = "no", "Non"

    debate = models.ForeignKey(Debate, on_delete=models.CASCADE, related_name="stances")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stances")
    choice = models.CharField(max_length=5, choices=Choice.choices)
    text = models.CharField("ton argument", max_length=500, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]
        constraints = [models.UniqueConstraint(fields=["debate", "user"], name="one_stance_per_member")]
