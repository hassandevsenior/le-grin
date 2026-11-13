# Le Grin

Une plateforme d'échange pour les développeurs, par les développeurs. Projet CADEV 2026.

Au Burkina, le *grin* est le cercle où l'on se retrouve autour du thé pour discuter. Celui-ci est pour les devs.

## Ce que fait la plateforme

| Le sujet demande | Réponse du Grin | Ce qui est différent |
|---|---|---|
| Se rencontrer | Débat du moment + annuaire des membres | On vote avant d'avoir un compte ; le vote devient le premier message à l'inscription |
| Partager ses projets | **Le mur** : capture d'écran obligatoire | **Retours épinglés** : chaque retour est posé à un endroit précis de la capture |
| Apprendre | **Parcours** | La communauté découpe en 7 étapes maximum, puis résume chaque étape (un lien seul est refusé) |
| Collaborer | **Coups de main** | On s'engage pour une durée choisie, qui expire. Seule réputation : les engagements tenus |

## Lancer en local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo        # données fictives, compte d'essai : demo / grin-demo-2026
python manage.py runserver
python manage.py test             # 29 tests
```

`python manage.py seed_demo --clear` recrée le jeu de démonstration. Pour l'enlever sans le recréer, supprimer les comptes en `@demo.grin` dans `/admin/` (`python manage.py createsuperuser` pour y accéder).

## Architecture

```
config/     réglages (tout ce qui varie passe par des variables d'environnement), routes
core/       Tech, Notification, accueil, annuaire, en-tête CSP, outils JSON, seed_demo
accounts/   utilisateur personnalisé, connexion par pseudo ou e-mail, profil
projects/   le mur, retours épinglés (Pin), traitement des captures (images.py)
collabs/    coups de main, engagements à durée limitée, fil d'avancement
paths/      parcours, étapes, explications, progression
debates/    débat du moment, vote avant inscription (services.py)
templates/  gabarits Django      static/  un fichier CSS, un fichier JS, aucun framework
tests/      les règles métier, testées
```

Choix techniques, et pourquoi :

- **Rendu côté serveur, JavaScript natif en amélioration.** Les pages pèsent quelques dizaines de Ko et marchent sur une connexion lente. Le JS (environ 350 lignes) ne sert qu'aux retours épinglés, aux boutons à bascule et au dépôt de capture.
- **Aucune ressource externe.** Pas de CDN, pas de police distante, pas de traceur. Un en-tête Content-Security-Policy l'impose au navigateur (`core/middleware.py`).
- **Captures jamais stockées telles quelles.** Elles sont ouvertes avec Pillow, vérifiées, recadrées, réduites à 1440 px et réencodées en WebP (`projects/images.py`). Un faux fichier image est refusé.
- **Expiration sans tâche planifiée.** Un engagement est « expiré » si sa date de fin est passée : c'est calculé à la lecture (`Commitment.is_expired`), rien à faire tourner en arrière-plan.
- **SQLite en mode WAL.** Aucun service à administrer, suffisant pour la charge du concours.
- **Sécurité.** CSRF sur tous les formulaires et appels `fetch`, échappement automatique des gabarits, droits vérifiés côté serveur sur chaque action, HTTPS/HSTS et cookies sécurisés en production, `manage.py check --deploy` propre.

## Déployer (VPS Datacloud, Ubuntu)

```bash
sudo adduser --system --group --home /srv/grin grin
# copier le code dans /srv/grin, puis en tant que grin :
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env              # remplir SECRET_KEY, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
set -a && . ./.env && set +a
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py createsuperuser
```

Puis `deploy/grin.service` (systemd) et `deploy/nginx.conf` (Nginx + `certbot` pour le HTTPS). Sans Nginx, `DJANGO_SERVE_MEDIA=1` laisse Django servir les captures. Tant que le HTTPS n'est pas en place, mettre `DJANGO_SSL_REDIRECT=0`.

Sauvegarde : le fichier SQLite et le dossier `media/`.

## Déclarations pour la soumission (article 6)

**Composants tiers, tous sous licence permissive :**

| Composant | Licence |
|---|---|
| Django 5.2 | BSD-3-Clause |
| Pillow | MIT-CMU (HPND) |
| WhiteNoise | MIT |
| Gunicorn | MIT |
| SQLite | domaine public |

Attention avant d'ajouter une dépendance : `psycopg` (PostgreSQL) est sous LGPL et `mysqlclient` sous GPL. Le règlement les rend irrecevables. C'est une des raisons du choix de SQLite.

**Intelligence artificielle :** à compléter par l'équipe (outil utilisé, parties concernées).
