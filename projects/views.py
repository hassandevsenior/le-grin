from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.http import api_post, toggle_membership
from core.models import Tech, notify

from .forms import PinForm, ProjectForm
from .models import Pin, Project

PINS_PER_MEMBER = 10  # par projet : assez pour un vrai retour, pas assez pour inonder


def pin_payload(pin, user):
    return {
        "id": pin.pk,
        "x": pin.x,
        "y": pin.y,
        "kind": pin.kind,
        "kindLabel": pin.get_kind_display(),
        "text": pin.text,
        "author": pin.author.username,
        "hue": pin.author.hue,
        "resolved": pin.resolved,
        "mine": pin.author_id == user.pk,
        "resolveUrl": reverse("projects:pin_resolve", args=[pin.pk]),
        "deleteUrl": reverse("projects:pin_delete", args=[pin.pk]),
    }


def project_list(request):
    projects = Project.objects.select_related("owner").prefetch_related("techs").annotate(
        pin_count=Count("pins", distinct=True), clap_count=Count("applause", distinct=True)
    )
    query = request.GET.get("q", "").strip()
    tech = request.GET.get("tech", "").strip()
    stage = request.GET.get("etat", "").strip()
    sort = request.GET.get("tri", "").strip()
    if query:
        projects = projects.filter(
            Q(title__icontains=query)
            | Q(tagline__icontains=query)
            | Q(description__icontains=query)
            | Q(owner__username__icontains=query)
        )
    if tech:
        projects = projects.filter(techs__slug=tech)
    if stage in Project.Stage.values:
        projects = projects.filter(stage=stage)
    else:
        stage = ""
    if sort == "retours":
        # Ceux qui attendent encore des retours passent devant.
        projects = projects.order_by("pin_count", "-created")
    elif sort == "bravos":
        projects = projects.order_by("-clap_count", "-created")
    else:
        sort = ""
        projects = projects.order_by("-created")
    paginator = Paginator(projects, 12)
    page = paginator.get_page(request.GET.get("page"))

    if request.GET.get("fragment") == "1":
        from django.template.loader import render_to_string

        cards_html = "".join(
            render_to_string("_project_card.html", {"project": item}, request=request)
            for item in page.object_list
        )
        next_url = ""
        if page.has_next():
            params = request.GET.copy()
            params.pop("fragment", None)
            params["page"] = page.next_page_number()
            next_url = f"{request.path}?{params.urlencode()}"
        return JsonResponse(
            {
                "html": cards_html,
                "has_next": page.has_next(),
                "next_url": next_url,
                "page": page.number,
                "num_pages": paginator.num_pages,
            }
        )

    active_tech = Tech.objects.filter(slug=tech).first() if tech else None
    context = {
        "page": page,
        "total_count": paginator.count,
        "query": query,
        "tech": tech,
        "active_tech": active_tech,
        "stage": stage,
        "active_stage_label": dict(Project.Stage.choices).get(stage, ""),
        "sort": sort,
        "has_filters": bool(query or tech or stage or sort),
        "stages": Project.Stage.choices,
        "techs": Tech.objects.annotate(n=Count("projects")).filter(n__gt=0).order_by("-n")[:12],
    }
    return render(request, "projects/list.html", context)


def detail(request, slug):
    project = get_object_or_404(Project.objects.select_related("owner").prefetch_related("techs"), slug=slug)
    pins = project.pins.select_related("author")
    context = {
        "project": project,
        "og_image_url": request.build_absolute_uri(project.screenshot.url),
        "pins": pins,
        "pins_data": [pin_payload(pin, request.user) for pin in pins],
        "clap_count": project.applause.count(),
        "clapped": request.user.is_authenticated and project.applause.filter(pk=request.user.pk).exists(),
        "is_owner": request.user == project.owner,
        "kinds": Pin.Kind.choices,
        "help_requests": project.help_requests.filter(is_open=True),
    }
    return render(request, "projects/detail.html", context)


@login_required
def create(request):
    form = ProjectForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        project = form.save(owner=request.user)
        messages.success(request, "Ton projet est au mur. Les retours vont arriver sur la capture.")
        return redirect(project)
    return render(request, "projects/form.html", {"form": form})


@login_required
def edit(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if project.owner != request.user:
        raise PermissionDenied
    form = ProjectForm(request.POST or None, request.FILES or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Projet mis à jour.")
        return redirect(project)
    return render(request, "projects/form.html", {"form": form, "project": project})


@login_required
@require_POST
def delete(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if project.owner != request.user:
        raise PermissionDenied
    project.screenshot.delete(save=False)
    project.delete()
    messages.success(request, "Projet retiré du mur.")
    return redirect("projects:list")


@api_post
def applaud(request, slug):
    project = get_object_or_404(Project, slug=slug)
    active, count = toggle_membership(project.applause, request.user)
    if active:
        notify(project.owner, request.user, f"{request.user.username} salue {project.title}", project.get_absolute_url())
    return JsonResponse({"active": active, "count": count})


@api_post
def pin_create(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if project.pins.filter(author=request.user).count() >= PINS_PER_MEMBER:
        return JsonResponse({"error": "Tu as déjà posé beaucoup de retours sur ce projet."}, status=429)
    form = PinForm(request.POST)
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        return JsonResponse({"error": first_error}, status=400)
    pin = form.save(commit=False)
    pin.project, pin.author = project, request.user
    pin.save()
    notify(
        project.owner, request.user,
        f"{request.user.username} a posé un retour sur {project.title}",
        f"{project.get_absolute_url()}#pin-{pin.pk}",
    )
    return JsonResponse({"pin": pin_payload(pin, request.user)}, status=201)


@api_post
def pin_resolve(request, pk):
    """Le porteur du projet coche un retour comme « pris en compte » (ou le rouvre)."""
    pin = get_object_or_404(Pin.objects.select_related("project"), pk=pk)
    if pin.project.owner != request.user:
        return JsonResponse({"error": "Seul le porteur du projet peut faire ça."}, status=403)
    pin.resolved = not pin.resolved
    pin.save(update_fields=["resolved"])
    if pin.resolved:
        notify(
            pin.author, request.user,
            f"Ton retour sur {pin.project.title} a été pris en compte",
            pin.project.get_absolute_url(),
        )
    return JsonResponse({"resolved": pin.resolved})


@api_post
def pin_delete(request, pk):
    pin = get_object_or_404(Pin.objects.select_related("project"), pk=pk)
    if request.user not in (pin.author, pin.project.owner):
        return JsonResponse({"error": "Ce retour n'est pas le tien."}, status=403)
    pin.delete()
    return JsonResponse({"deleted": True})
