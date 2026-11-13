"""
Logique du débat partagée entre la page d'accueil, la page du débat et l'inscription.

Un visiteur peut voter avant d'avoir un compte : son choix attend dans la
session, puis devient son premier avis publié dès qu'il s'inscrit.
"""

from .models import Debate, Stance

SESSION_KEY = "pending_stance"


def remember_choice(request, debate, choice):
    request.session[SESSION_KEY] = {"debate": debate.pk, "choice": choice}


def pending_choice(request, debate):
    pending = request.session.get(SESSION_KEY) or {}
    return pending.get("choice") if pending.get("debate") == debate.pk else None


def publish_pending(request, user):
    """Transforme le choix en attente en avis publié. Renvoie le débat concerné, ou None."""
    pending = request.session.pop(SESSION_KEY, None)
    if not pending or pending.get("choice") not in Stance.Choice.values:
        return None
    debate = Debate.objects.filter(pk=pending.get("debate")).first()
    if debate:
        Stance.objects.get_or_create(debate=debate, user=user, defaults={"choice": pending["choice"]})
    return debate


def stance_context(request, debate):
    """Ce dont un gabarit a besoin pour afficher le bloc de vote d'un débat."""
    stance = None
    if request.user.is_authenticated:
        stance = Stance.objects.filter(debate=debate, user=request.user).first()
    chosen = stance.choice if stance else pending_choice(request, debate)
    return {"tally": debate.tally(), "my_stance": stance, "chosen": chosen}
