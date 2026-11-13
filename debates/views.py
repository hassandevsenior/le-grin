from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Debate, Stance
from .services import remember_choice, stance_context


def debate_list(request):
    debates = Debate.objects.annotate(voices=Count("stances")).order_by("-featured", "-created")
    return render(request, "debates/list.html", {"debates": debates})


def detail(request, slug):
    debate = get_object_or_404(Debate, slug=slug)
    stances = debate.stances.exclude(text="").select_related("user")
    side = request.GET.get("avis", "")
    if side in Stance.Choice.values:
        stances = stances.filter(choice=side)
    context = {"debate": debate, "stances": stances[:60], "side": side}
    context.update(stance_context(request, debate))
    return render(request, "debates/detail.html", context)


@require_POST
def vote(request, slug):
    debate = get_object_or_404(Debate, slug=slug)
    choice = request.POST.get("choice", "")
    if choice not in Stance.Choice.values:
        messages.error(request, "Choisis une des trois réponses.")
        return redirect(debate)

    if not request.user.is_authenticated:
        # Pas encore de compte : on garde le choix au chaud, il sera publié à l'inscription.
        remember_choice(request, debate, choice)
        if request.POST.get("back") == "home":
            return redirect("/#debat")
        return redirect(debate)

    text = request.POST.get("text", "").strip()[:500]
    stance, created = Stance.objects.get_or_create(
        debate=debate, user=request.user, defaults={"choice": choice, "text": text}
    )
    if not created:
        stance.choice = choice
        if "text" in request.POST:
            stance.text = text
        stance.save()
    if text:
        messages.success(request, "Ton avis est publié.")
    return redirect(debate)
