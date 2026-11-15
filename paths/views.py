from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.http import api_post, toggle_membership
from core.models import Tech, notify

from .forms import ExplanationForm, PathForm, StepForm
from .models import MAX_STEPS, Explanation, Path, Step


def path_list(request):
    paths = Path.objects.select_related("author", "tech").annotate(
        step_count=Count("steps", distinct=True),
        explanation_count=Count("steps__explanations", distinct=True),
    ).order_by("-created")
    query = request.GET.get("q", "").strip()
    tech = request.GET.get("tech", "").strip()
    show = request.GET.get("voir", "").strip()
    if show != "a-tracer":
        show = ""
    if show == "a-tracer":
        paths = paths.filter(step_count__lt=3)
    if tech:
        paths = paths.filter(tech__slug=tech)
    if query:
        paths = paths.filter(
            Q(title__icontains=query)
            | Q(context__icontains=query)
            | Q(tech__name__icontains=query)
            | Q(author__username__icontains=query)
        )
    items = list(paths[:60])
    active_tech = Tech.objects.filter(slug=tech).first() if tech else None
    return render(
        request,
        "paths/list.html",
        {
            "paths": items,
            "total_count": len(items),
            "query": query,
            "tech": tech,
            "active_tech": active_tech,
            "show": show,
            "has_filters": bool(query or tech or show),
            "techs": Tech.objects.annotate(n=Count("paths")).filter(n__gt=0).order_by("-n")[:12],
        },
    )


def detail(request, pk):
    explanations = Explanation.objects.select_related("author").prefetch_related("thanks")
    path = get_object_or_404(
        Path.objects.select_related("author", "tech").prefetch_related(
            Prefetch("steps", Step.objects.select_related("author").prefetch_related(
                Prefetch("explanations", explanations), "done_by"
            ))
        ),
        pk=pk,
    )
    steps = list(path.steps.all())
    done = 0
    if request.user.is_authenticated:
        done = sum(1 for step in steps if any(u.pk == request.user.pk for u in step.done_by.all()))
    context = {
        "path": path,
        "steps": steps,
        "done": done,
        "percent": round(100 * done / len(steps)) if steps else 0,
        "can_add_step": len(steps) < MAX_STEPS,
        "max_steps": MAX_STEPS,
        "is_author": request.user == path.author,
        "step_form": StepForm(),
        "explanation_form": ExplanationForm(),
    }
    return render(request, "paths/detail.html", context)


@login_required
def create(request):
    form = PathForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        path = form.save(author=request.user)
        messages.success(request, "C'est lancé. Les membres vont tracer les étapes pour toi : tu seras prévenu à chaque nouvelle.")
        return redirect(path)
    return render(request, "paths/form.html", {"form": form})


@login_required
@require_POST
def add_step(request, pk):
    path = get_object_or_404(Path, pk=pk)
    if path.author == request.user:
        messages.error(request, "Ce sont les membres qui tracent ton parcours : tu n'as pas à proposer d'étapes.")
        return redirect(path)
    form = StepForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Donne un titre à l'étape.")
        return redirect(path)
    with transaction.atomic():
        if path.steps.count() >= MAX_STEPS:
            messages.error(request, f"Ce parcours a déjà ses {MAX_STEPS} étapes : mieux vaut les expliquer.")
            return redirect(path)
        step = form.save(commit=False)
        step.path, step.author = path, request.user
        step.position = (path.steps.aggregate(last=Max("position"))["last"] or 0) + 1
        step.save()
    notify(path.author, request.user, f"{request.user.username} propose une étape pour « {path.title} »", path.get_absolute_url())
    return redirect(f"{path.get_absolute_url()}#etape-{step.pk}")


@login_required
@require_POST
def move_step(request, pk):
    """L'auteur du parcours remonte une étape d'un cran (échange avec la précédente)."""
    step = get_object_or_404(Step.objects.select_related("path"), pk=pk)
    if step.path.author != request.user:
        raise PermissionDenied
    previous = step.path.steps.filter(position__lt=step.position).order_by("-position").first()
    if previous:
        with transaction.atomic():
            step.position, previous.position = previous.position, step.position
            step.save(update_fields=["position"])
            previous.save(update_fields=["position"])
    return redirect(step.path)


@login_required
@require_POST
def delete_step(request, pk):
    step = get_object_or_404(Step.objects.select_related("path"), pk=pk)
    if request.user not in (step.author, step.path.author):
        raise PermissionDenied
    if step.explanations.exists() and request.user != step.path.author:
        messages.error(request, "Cette étape a déjà des explications : seul l'auteur du parcours peut la retirer.")
    else:
        step.delete()
    return redirect(step.path)


@login_required
@require_POST
def add_explanation(request, pk):
    step = get_object_or_404(Step.objects.select_related("path"), pk=pk)
    anchor = f"{step.path.get_absolute_url()}#etape-{step.pk}"
    if step.path.author == request.user:
        messages.error(request, "Tu as demandé ce parcours : ce sont les autres membres qui expliquent les étapes.")
        return redirect(anchor)
    form = ExplanationForm(request.POST)
    if not form.is_valid():
        messages.error(request, next(iter(form.errors.values()))[0])
        return redirect(anchor)
    explanation = form.save(commit=False)
    explanation.step, explanation.author = step, request.user
    explanation.save()
    notify(step.path.author, request.user, f"{request.user.username} explique « {step.title} »", anchor)
    return redirect(anchor)


@api_post
def toggle_done(request, pk):
    step = get_object_or_404(Step, pk=pk)
    active, _ = toggle_membership(step.done_by, request.user)
    total = step.path.steps.count()
    done = step.path.steps.filter(done_by=request.user).count()
    return JsonResponse({"active": active, "done": done, "total": total, "percent": round(100 * done / total)})


@api_post
def thank(request, pk):
    explanation = get_object_or_404(Explanation.objects.select_related("step__path"), pk=pk)
    if explanation.author == request.user:
        return JsonResponse({"error": "C'est ta propre explication."}, status=400)
    active, count = toggle_membership(explanation.thanks, request.user)
    if active:
        notify(
            explanation.author, request.user,
            f"{request.user.username} te remercie pour ton explication",
            f"{explanation.step.path.get_absolute_url()}#etape-{explanation.step_id}",
        )
    return JsonResponse({"active": active, "count": count})
