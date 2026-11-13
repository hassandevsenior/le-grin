"""
Remplit le Grin avec un jeu de données de démonstration.

    python manage.py seed_demo

Tous les comptes créés ont le mot de passe DEMO_PASSWORD et une adresse en
@demo.grin : ils sont fictifs. `python manage.py seed_demo --clear` les retire
(et tout ce qu'ils ont publié) avant de recréer le jeu.
"""

import random
import unicodedata
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from collabs.models import Commitment, HelpRequest, Update
from core.models import Tech
from debates.models import Debate, Stance
from paths.models import Explanation, Path, Step
from projects.forms import unique_slug
from projects.models import Pin, Project

User = get_user_model()
DEMO_PASSWORD = "grin-demo-2026"
DEMO_DOMAIN = "demo.grin"

MEMBERS = [
    ("awa", "senior", "Bobo-Dioulasso", "Backend depuis dix ans. J'aime les systèmes simples qui tiennent la charge.", "Django, PostgreSQL, Docker"),
    ("ibrahim", "confirmed", "Ouagadougou", "Mobile d'abord, parce que c'est là que sont nos utilisateurs.", "Flutter, Dart, Firebase"),
    ("fatou", "junior", "Dakar", "Front-end et accessibilité. Je pose beaucoup de questions.", "JavaScript, CSS, Vue.js"),
    ("moussa", "learning", "Banfora", "Étudiant en deuxième année, j'apprends Python le soir.", "Python, Git"),
    ("clarisse", "confirmed", "Abidjan", "Data et automatisation pour les PME.", "Python, Pandas, FastAPI"),
    ("yacouba", "senior", "Lomé", "DevOps. Si ça ne se redéploie pas en une commande, ce n'est pas fini.", "Linux, Nginx, Docker, Ansible"),
    ("mariam", "junior", "Bobo-Dioulasso", "Je construis des outils pour les commerçantes du marché.", "Django, JavaScript, SQLite"),
    ("demo", "junior", "Bobo-Dioulasso", "Compte de démonstration : connecte-toi et essaie tout.", "Django, JavaScript"),
]

PROJECTS = [
    ("mariam", "Sugu", "Le carnet de crédit des commerçantes, sur téléphone.", "live", "https://sugu.example.bf", "https://github.com/example/sugu", "Django, JavaScript, SQLite", ("#fff7e8", "#d9480f", "#2b2118"),
     "Au marché, les crédits clients se notent dans un cahier qui se perd. Sugu remplace le cahier, fonctionne hors connexion et envoie un rappel par SMS.\n\nLe plus dur : la synchronisation quand le réseau revient."),
    ("ibrahim", "Taxi Brousse", "Savoir à quelle heure part vraiment le prochain car.", "building", "", "https://github.com/example/taxi-brousse", "Flutter, Firebase", ("#0f2a3d", "#ffd43b", "#ffffff"),
     "Les horaires affichés en gare ne sont jamais les bons. Les voyageurs signalent les départs réels, l'appli en déduit l'heure probable."),
    ("clarisse", "Kalan", "Des annales corrigées pas à pas pour les lycéens.", "live", "https://kalan.example.ci", "", "FastAPI, Vue.js, PostgreSQL", ("#eef6f1", "#1f6b5a", "#13241f"),
     "Chaque correction est découpée en étapes qu'on dévoile une à une, pour chercher avant de lire la réponse."),
    ("awa", "Faso Paie", "Une API de paiement mobile unifiée pour Orange Money et Moov.", "building", "https://fasopaie.example.bf", "https://github.com/example/faso-paie", "Django, PostgreSQL, Docker", ("#16121f", "#9775fa", "#f4f0ff"),
     "Intégrer deux opérateurs, c'est deux API, deux formats, deux façons d'échouer. Une seule interface, des webhooks fiables, un bac à sable."),
    ("fatou", "Tônô", "Un lecteur d'écran mis à l'épreuve sur les sites publics d'Afrique de l'Ouest.", "idea", "", "https://github.com/example/tono", "JavaScript, CSS", ("#fdf0f0", "#c2255c", "#2b1220"),
     "Un tableau de bord qui note l'accessibilité des sites administratifs et explique comment corriger chaque problème."),
    ("yacouba", "Deploie", "Mettre en ligne une app Django sur un VPS en une commande.", "live", "https://deploie.example.tg", "https://github.com/example/deploie", "Ansible, Nginx, Linux", ("#101418", "#51cf66", "#e9f5ec"),
     "Né de la dixième fois où j'ai configuré Nginx et systemd à la main pour quelqu'un."),
]

PINS = [
    ("love", 28, 30, "Le titre dit exactement ce que ça fait. On comprend en deux secondes."),
    ("idea", 70, 42, "Je mettrais un exemple concret ici plutôt qu'une illustration."),
    ("bug", 82, 7, "Sur mon téléphone ce menu passe sous le logo."),
    ("idea", 32, 58, "Le bouton principal mériterait plus de contraste."),
    ("love", 50, 82, "Les trois blocs du bas se lisent très bien."),
]

DEBATES = [
    ("L'IA va-t-elle remplacer les développeurs ?", "Ou seulement changer ce qu'on appelle développer ?", True, [
        ("awa", "no", "Elle remplace la frappe, pas la compréhension. Quelqu'un doit toujours savoir pourquoi le système est fait comme ça, et répondre quand il casse à trois heures du matin."),
        ("moussa", "yes", "J'apprends à coder et l'IA écrit déjà mieux que moi. Je me demande ce qu'il restera pour les juniors dans cinq ans."),
        ("clarisse", "mixed", "Il faudra moins de gens pour écrire du code, plus pour décider quoi construire. Ceux qui comprennent le métier du client ne risquent rien."),
        ("yacouba", "no", "J'ai vu du code généré partir en production sans que personne ne le comprenne. Ça crée du travail pour dix ans."),
        ("fatou", "mixed", "Elle remplace le dev qui refuse de s'en servir, pas les autres."),
    ]),
    ("Faut-il encore apprendre le JavaScript natif avant un framework ?", "", False, [
        ("fatou", "yes", "Le jour où le framework change, il te reste le langage."),
        ("ibrahim", "mixed", "Apprends les deux en même temps sur un vrai projet. Personne ne reste motivé avec des exercices."),
    ]),
    ("Un développeur doit-il savoir déployer lui-même ?", "", False, [
        ("yacouba", "yes", "Si tu n'as jamais mis en production, tu ne sais pas ce que ton code coûte."),
    ]),
]

PATHS = [
    ("moussa", "Déployer une app Django sur un VPS", "Django", "Mon projet tourne sur mon PC avec runserver. Je n'ai jamais touché à un serveur. J'ai un VPS Ubuntu vide.", [
        ("yacouba", "Se connecter au serveur en SSH avec une clé", "Sans ça, rien d'autre n'est possible.",
         [("yacouba", "Une clé SSH, c'est une paire : la partie privée reste sur ton PC, la partie publique va sur le serveur. Tu la crées avec ssh-keygen, tu l'envoies avec ssh-copy-id, puis tu coupes la connexion par mot de passe. Résultat : personne ne peut deviner ton accès.", "https://www.ssh.com/academy/ssh/keygen")]),
        ("awa", "Préparer Django pour la production", "DEBUG=False change beaucoup de choses.",
         [("awa", "Trois réglages comptent : DEBUG à False, la SECRET_KEY lue depuis une variable d'environnement, et ALLOWED_HOSTS avec ton domaine. Lance ensuite manage.py check --deploy : Django te liste lui-même ce qu'il manque.", "https://docs.djangoproject.com/fr/5.2/howto/deployment/checklist/"),
          ("mariam", "Pense aussi à collectstatic : en production Django ne sert plus tes fichiers CSS et JS tout seul. WhiteNoise règle ça en deux lignes, sans rien configurer côté Nginx.", "")]),
        ("yacouba", "Lancer l'app avec Gunicorn et systemd", "Pour qu'elle redémarre toute seule.",
         [("yacouba", "runserver est fait pour ton PC. Gunicorn est le vrai serveur d'application : il lance plusieurs processus de ton app. systemd le surveille : si l'app plante ou si le serveur redémarre, elle repart sans toi.", "")]),
        ("awa", "Mettre Nginx devant, avec HTTPS", "C'est la porte d'entrée publique.", []),
    ]),
    ("fatou", "Comprendre Git au-delà de add, commit, push", "Git", "Je sais sauvegarder mon travail mais je panique dès qu'il y a un conflit.", [
        ("ibrahim", "Voir un commit comme une photo, pas comme une différence", "Tout le reste en découle.",
         [("ibrahim", "Chaque commit est une photo complète de ton projet, reliée à la photo précédente. Une branche n'est qu'une étiquette posée sur une photo. Quand tu as ça en tête, merge et rebase deviennent logiques : ce sont deux façons de relier des photos.", "https://git-scm.com/book/fr/v2")]),
        ("awa", "Résoudre un conflit à la main, une fois, lentement", "", []),
    ]),
    ("mariam", "Apprendre Flutter quand on vient du web", "Flutter", "Je connais HTML, CSS et un peu de JavaScript.", []),
]

HELP = [
    ("mariam", "Sugu", "La synchronisation hors ligne duplique des ventes", "days",
     "Quand deux téléphones enregistrent une vente sans réseau puis se reconnectent, la vente apparaît deux fois.\n\nJ'ai essayé un identifiant généré côté serveur, mais il n'existe pas encore au moment de la saisie. Je cherche quelqu'un qui a déjà géré ce genre de synchronisation.",
     [("awa", 7, "J'ai eu exactement ce problème sur un projet de caisse. Je regarde ton modèle ce soir.", "active", 2),
      ("clarisse", 3, "Je peux relire la logique de fusion.", "kept", 5)],
     [("awa", "Le souci vient de l'identifiant. Génère un UUID sur le téléphone au moment de la vente : le serveur peut alors reconnaître une vente déjà reçue."),
      ("mariam", "Testé avec deux téléphones en mode avion : plus de doublon. Il me reste à migrer les anciennes ventes.")]),
    ("ibrahim", "Taxi Brousse", "Notifications push qui n'arrivent pas sur certains Tecno", "hours",
     "Sur plusieurs téléphones Tecno et Infinix, les notifications n'arrivent que quand l'appli est ouverte. Sur Samsung tout va bien.", [], []),
    ("moussa", None, "Relire mon premier projet Django avant ma soutenance", "hours",
     "C'est une petite gestion de bibliothèque. Ça marche, mais je ne sais pas si c'est bien fait. J'aimerais un regard franc sur l'organisation des vues et des modèles.",
     [("yacouba", 1, "", "active", 3)], []),
    ("awa", "Faso Paie", "Cherche quelqu'un pour écrire le SDK JavaScript", "weeks",
     "L'API est stable. Il manque un petit client JavaScript bien documenté pour que les intégrateurs n'aient pas à lire toute la référence.", [], []),
]


def font(size):
    """Une police qui connaît les accents si le système en a une, sinon celle de Pillow."""
    for name in ("DejaVuSans.ttf", "LiberationSans-Regular.ttf", "NotoSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def plain(text):
    """Retire les accents : la police de secours de Pillow ne les dessine pas."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def fake_landing(title, tagline, palette, seed):
    """Dessine une fausse page d'accueil : assez crédible pour faire vivre le mur."""
    background, accent, ink = palette
    if font(20).getname()[0] == "Aileron":  # police de secours de Pillow
        title, tagline = plain(title), plain(tagline)
    rng = random.Random(seed)
    width, height = 1280, 1500
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)

    draw.text((70, 44), title, fill=accent, font=font(34))
    for index, label in enumerate(["Produit", "Tarifs", "Contact"]):
        draw.text((820 + index * 130, 52), label, fill=ink, font=font(22))
    draw.rounded_rectangle((1090, 40, 1210, 92), 26, fill=accent)

    words, lines, line = tagline.split(), [], ""
    for word in words:
        if len(line) + len(word) > 22:
            lines.append(line)
            line = ""
        line = f"{line} {word}".strip()
    lines.append(line)
    for index, text in enumerate(lines[:4]):
        draw.text((70, 210 + index * 86), text, fill=ink, font=font(72))
    top = 240 + len(lines[:4]) * 86
    draw.rounded_rectangle((70, top, 330, top + 72), 36, fill=accent)
    draw.rounded_rectangle((350, top, 560, top + 72), 36, outline=ink, width=3)

    draw.rounded_rectangle((760, 190, 1210, 640), 32, fill=accent)
    for index in range(4):
        y = 250 + index * 90
        draw.rounded_rectangle((810, y, 810 + rng.randint(180, 340), y + 34), 17, fill=background)

    for column in range(3):
        x = 70 + column * 390
        draw.rounded_rectangle((x, 800, x + 360, 1110), 24, outline=accent, width=3)
        draw.ellipse((x + 30, 830, x + 100, 900), fill=accent)
        for row in range(3):
            draw.rounded_rectangle((x + 30, 940 + row * 46, x + 30 + rng.randint(160, 290), 962 + row * 46), 11, fill=ink)

    draw.rectangle((0, 1240, width, height), fill=accent)
    draw.text((70, 1330), f"Essayez {title} aujourd'hui", fill=background, font=font(52))

    buffer = BytesIO()
    image.save(buffer, "WEBP", quality=78)
    return ContentFile(buffer.getvalue(), name=f"demo-{title.lower().replace(' ', '-')}.webp")


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration (comptes fictifs en @demo.grin)."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Retire d'abord les données de démonstration.")

    @transaction.atomic
    def handle(self, *args, **options):
        demo_users = User.objects.filter(email__endswith=f"@{DEMO_DOMAIN}")
        if options["clear"]:
            for project in Project.objects.filter(owner__in=demo_users):
                project.screenshot.delete(save=False)
            demo_users.delete()
            Debate.objects.filter(stances__isnull=True).delete()
        elif demo_users.exists():
            self.stdout.write("Les données de démonstration existent déjà (--clear pour repartir de zéro).")
            return

        now = timezone.now()
        users = {}
        for name, level, city, bio, techs in MEMBERS:
            user = User.objects.create_user(
                username=name, email=f"{name}@{DEMO_DOMAIN}", password=DEMO_PASSWORD,
                level=level, city=city, bio=bio,
            )
            user.techs.set(Tech.from_text(techs))
            users[name] = user

        projects = {}
        for index, (owner, title, tagline, stage, live, repo, techs, palette, story) in enumerate(PROJECTS):
            project = Project.objects.create(
                owner=users[owner], title=title, slug=unique_slug(title), tagline=tagline, stage=stage,
                live_url=live, repo_url=repo, description=story,
                screenshot=fake_landing(title, tagline, palette, seed=index),
            )
            project.techs.set(Tech.from_text(techs))
            Project.objects.filter(pk=project.pk).update(created=now - timedelta(hours=7 * index + 2))
            others = [user for name, user in users.items() if name not in (owner, "demo")]
            rng = random.Random(index)
            project.applause.set(rng.sample(others, rng.randint(2, len(others))))
            for kind, x, y, text in rng.sample(PINS, rng.randint(0, 4) if index else 4):
                Pin.objects.create(project=project, author=rng.choice(others), kind=kind, x=x, y=y, text=text)
            projects[title] = project
        first_pin = projects["Sugu"].pins.first()
        if first_pin:
            first_pin.resolved = True
            first_pin.save()

        for question, intro, featured, stances in DEBATES:
            debate, _ = Debate.objects.get_or_create(
                slug=slugify(question)[:80], defaults={"question": question, "intro": intro, "featured": featured}
            )
            for name, choice, text in stances:
                Stance.objects.get_or_create(debate=debate, user=users[name], defaults={"choice": choice, "text": text})

        for path_index, (author, title, tech, context, steps) in enumerate(PATHS):
            path = Path.objects.create(
                author=users[author], title=title, context=context, tech=Tech.from_text(tech, limit=1)[0]
            )
            Path.objects.filter(pk=path.pk).update(created=now - timedelta(days=1 + 2 * path_index))
            for position, (step_author, step_title, why, explanations) in enumerate(steps, start=1):
                step = Step.objects.create(
                    path=path, author=users[step_author], position=position, title=step_title, why=why
                )
                for explainer, summary, url in explanations:
                    explanation = Explanation.objects.create(
                        step=step, author=users[explainer], summary=summary, resource_url=url
                    )
                    explanation.thanks.add(users[author])

        for index, (author, project, title, size, details, commitments, updates) in enumerate(HELP):
            help_request = HelpRequest.objects.create(
                author=users[author], project=projects.get(project), title=title, size=size, details=details,
                repo_url=projects[project].repo_url if project else "",
            )
            HelpRequest.objects.filter(pk=help_request.pk).update(created=now - timedelta(hours=5 + 9 * index))
            for name, days, message, status, age in commitments:
                commitment = Commitment.objects.create(
                    request=help_request, user=users[name], days=days, message=message, status=status
                )
                started = now - timedelta(days=age if status == "kept" else min(age, days - 1) * 0.6)
                Commitment.objects.filter(pk=commitment.pk).update(
                    created=started, ends_at=started + timedelta(days=days)
                )
            for position, (name, text) in enumerate(updates):
                update = Update.objects.create(request=help_request, author=users[name], text=text)
                Update.objects.filter(pk=update.pk).update(created=now - timedelta(hours=4 - 3 * position))

        self.stdout.write(self.style.SUCCESS(
            f"Jeu de démonstration créé : {len(users)} comptes (mot de passe « {DEMO_PASSWORD} »), "
            f"{len(projects)} projets. Compte d'essai : demo / {DEMO_PASSWORD}"
        ))


