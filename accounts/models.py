from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse

from core.models import Tech


class User(AbstractUser):
    class Level(models.TextChoices):
        LEARNING = "learning", "En apprentissage"
        JUNIOR = "junior", "Junior"
        CONFIRMED = "confirmed", "Confirmé"
        SENIOR = "senior", "Senior"

    email = models.EmailField("adresse e-mail", unique=True)
    level = models.CharField("niveau", max_length=12, choices=Level.choices, default=Level.LEARNING)
    bio = models.CharField("en une phrase", max_length=200, blank=True)
    city = models.CharField("ville", max_length=60, blank=True)
    github = models.URLField("profil GitHub", blank=True)
    techs = models.ManyToManyField(Tech, blank=True, related_name="members")

    def get_absolute_url(self):
        return reverse("accounts:profile", args=[self.username])

    @property
    def initials(self):
        return self.username[:2].upper()

    @property
    def hue(self):
        """Teinte stable (0-359) dérivée du pseudo, pour un avatar sans image."""
        return sum(ord(char) * (index + 7) for index, char in enumerate(self.username)) % 360

    @property
    def kept_count(self):
        """Nombre d'engagements tenus : la seule « réputation » du Grin."""
        return self.commitments.filter(status="kept").count()
