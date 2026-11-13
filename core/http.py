"""Petits outils partagés par les points d'entrée appelés en JavaScript (fetch)."""

from functools import wraps

from django.http import JsonResponse
from django.views.decorators.http import require_POST


def api_post(view):
    """POST uniquement, membre connecté obligatoire ; répond en JSON plutôt qu'en redirection."""

    @require_POST
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Connecte-toi pour faire ça."}, status=401)
        return view(request, *args, **kwargs)

    return wrapper


def toggle_membership(relation, user):
    """Ajoute ou retire `user` d'une relation plusieurs-à-plusieurs. Renvoie (actif, total)."""
    if relation.filter(pk=user.pk).exists():
        relation.remove(user)
        active = False
    else:
        relation.add(user)
        active = True
    return active, relation.count()
