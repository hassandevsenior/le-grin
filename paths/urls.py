from django.urls import path

from . import views

app_name = "paths"

urlpatterns = [
    path("", views.path_list, name="list"),
    path("nouveau/", views.create, name="create"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/etapes/", views.add_step, name="add_step"),
    path("etapes/<int:pk>/monter/", views.move_step, name="move_step"),
    path("etapes/<int:pk>/retirer/", views.delete_step, name="delete_step"),
    path("etapes/<int:pk>/expliquer/", views.add_explanation, name="explain"),
    path("etapes/<int:pk>/fait/", views.toggle_done, name="done"),
    path("explications/<int:pk>/merci/", views.thank, name="thank"),
]
