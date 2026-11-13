from django.urls import path

from . import views

app_name = "debates"

urlpatterns = [
    path("", views.debate_list, name="list"),
    path("<slug:slug>/", views.detail, name="detail"),
    path("<slug:slug>/avis/", views.vote, name="vote"),
]
