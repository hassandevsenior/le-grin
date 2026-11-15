"""Crée les débats de départ, sans aucun avis : la page d'accueil a toujours une question du moment.

Jusqu'ici ils n'existaient que dans le jeu de démonstration (seed_demo), donc pas en production.
Rien n'est écrasé : un débat déjà présent (même slug) est laissé tel quel.
"""

from django.db import migrations
from django.utils.text import slugify

DEBATS = [
    ("L'IA va-t-elle remplacer les développeurs ?", "Ou seulement changer ce qu'on appelle développer ?"),
    ("Faut-il encore apprendre le JavaScript natif avant un framework ?", ""),
    ("Un développeur doit-il savoir déployer lui-même ?", ""),
]


def creer(apps, schema_editor):
    Debate = apps.get_model("debates", "Debate")
    deja_une = Debate.objects.filter(featured=True).exists()
    for index, (question, intro) in enumerate(DEBATS):
        Debate.objects.get_or_create(
            slug=slugify(question)[:80],
            defaults={"question": question, "intro": intro, "featured": index == 0 and not deja_une},
        )


class Migration(migrations.Migration):
    dependencies = [("debates", "0001_initial")]
    operations = [migrations.RunPython(creer, migrations.RunPython.noop)]
