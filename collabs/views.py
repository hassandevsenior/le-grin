from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import notify

from .forms import CommitmentForm, HelpRequestForm, UpdateForm
from .models import Commitment, HelpRequest


def request_list(request):
    running = Q(commitments__status="active", commitments__ends_at__gt=timezone.now())
    requests = HelpRequest.objects.select_related("author", "project").annotate(
        helpers=Count("commitments", filter=running, distinct=True)
    ).order_by("-is_open", "-created")
    query = request.GET.get("q", "").strip()
    size = request.GET.get("taille", "").strip()
    show = request.GET.get("voir", "").strip()
    if show not in ("sans-renfort", "tout"):
        show = ""
    if show == "sans-renfort":
        requests = requests.filter(is_open=True, helpers=0)
    elif show != "tout":
        requests = requests.filter(is_open=True)
    if size in HelpRequest.Size.values:
        requests = requests.filter(size=size)
    else:
        size = ""
    if query:
        requests = requests.filter(
            Q(title__icontains=query)
            | Q(details__icontains=query)
            | Q(author__username__icontains=query)
            | Q(project__title__icontains=query)
        )
    items = list(requests[:60])
    return render(
        request,
        "collabs/list.html",
        {
            "requests": items,
            "total_count": len(items),
            "query": query,
            "size": size,
            "sizes": HelpRequest.Size.choices,
            "active_size_label": dict(HelpRequest.Size.choices).get(size, ""),
            "show": show,
            "has_filters": bool(query or size or show),
        },
    )


def detail(request, pk):
    help_request = get_object_or_404(HelpRequest.objects.select_related("author", "project"), pk=pk)
    commitments = list(help_request.commitments.select_related("user"))
    mine = next((c for c in commitments if c.user_id == request.user.pk), None)
    is_author = request.user == help_request.author
    context = {
        "help_request": help_request,
        "commitments": commitments,
        "mine": mine,
        "is_author": is_author,
        "can_post": is_author or mine is not None,
        "updates": help_request.updates.select_related("author"),
        "commit_form": CommitmentForm(),
        "update_form": UpdateForm(),
    }
    return render(request, "collabs/detail.html", context)


@login_required
def create(request):
    initial = {"project": request.GET.get("projet")}
    form = HelpRequestForm(request.POST or None, user=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        help_request = form.save(commit=False)
        help_request.author = request.user
        help_request.save()
        messages.success(request, "Ta demande est publiée.")
        return redirect(help_request)
    return render(request, "collabs/form.html", {"form": form})


@login_required
@require_POST
def commit(request, pk):
    help_request = get_object_or_404(HelpRequest, pk=pk, is_open=True)
    if help_request.author == request.user:
        raise PermissionDenied
    form = CommitmentForm(request.POST)
    if not form.is_valid():
        for errors in form.errors.values():
            messages.error(request, errors[0])
        return redirect(help_request.get_absolute_url() + "#engagement")

    previous = Commitment.objects.filter(request=help_request, user=request.user).first()
    if previous and previous.is_running:
        messages.info(request, "Tu es déjà engagé sur cette demande.")
        return redirect(help_request)
    if previous:
        # Un engagement expiré ou libéré peut être repris : on repart sur une nouvelle durée.
        previous.delete()
    commitment = form.save(commit=False)
    commitment.request, commitment.user = help_request, request.user
    try:
        commitment.save()
    except IntegrityError:
        return redirect(help_request)
    notify(
        help_request.author, request.user,
        f"{request.user.username} s'engage {commitment.get_days_display()} sur « {help_request.title} »",
        help_request.get_absolute_url(),
    )
    messages.success(request, f"Engagement pris pour {commitment.get_days_display()}. Merci.")
    return redirect(help_request)


@login_required
@require_POST
def release(request, pk):
    """Se libérer honnêtement vaut mieux que disparaître."""
    commitment = get_object_or_404(Commitment, request_id=pk, user=request.user, status="active")
    commitment.status = Commitment.Status.RELEASED
    commitment.save(update_fields=["status"])
    notify(
        commitment.request.author, request.user,
        f"{request.user.username} se libère de « {commitment.request.title} »",
        commitment.request.get_absolute_url(),
    )
    messages.info(request, "Tu es libéré de cet engagement. Merci de l'avoir dit.")
    return redirect(commitment.request)


@login_required
@require_POST
def mark_kept(request, pk, commitment_id):
    """L'auteur de la demande confirme qu'un engagement a été tenu."""
    commitment = get_object_or_404(Commitment.objects.select_related("request"), pk=commitment_id, request_id=pk)
    if commitment.request.author != request.user:
        raise PermissionDenied
    commitment.status = Commitment.Status.KEPT
    commitment.save(update_fields=["status"])
    notify(
        commitment.user, request.user,
        f"{request.user.username} confirme : engagement tenu sur « {commitment.request.title} »",
        commitment.request.get_absolute_url(),
    )
    return redirect(commitment.request)


@login_required
@require_POST
def toggle_open(request, pk):
    help_request = get_object_or_404(HelpRequest, pk=pk)
    if help_request.author != request.user:
        raise PermissionDenied
    help_request.is_open = not help_request.is_open
    help_request.save(update_fields=["is_open"])
    messages.success(request, "Demande rouverte." if help_request.is_open else "Demande marquée comme résolue.")
    return redirect(help_request)


@login_required
@require_POST
def add_update(request, pk):
    help_request = get_object_or_404(HelpRequest, pk=pk)
    engaged = help_request.commitments.filter(user=request.user).exists()
    if request.user != help_request.author and not engaged:
        raise PermissionDenied
    form = UpdateForm(request.POST)
    if form.is_valid():
        update = form.save(commit=False)
        update.request, update.author = help_request, request.user
        update.save()
        recipients = {help_request.author} | {c.user for c in help_request.commitments.select_related("user")}
        for recipient in recipients:
            notify(
                recipient, request.user,
                f"Nouveau point sur « {help_request.title} »",
                f"{help_request.get_absolute_url()}#fil",
            )
    return redirect(help_request.get_absolute_url() + "#fil")
