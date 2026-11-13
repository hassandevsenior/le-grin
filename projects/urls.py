from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("nouveau/", views.create, name="create"),
    path("retours/<int:pk>/traiter/", views.pin_resolve, name="pin_resolve"),
    path("retours/<int:pk>/supprimer/", views.pin_delete, name="pin_delete"),
    path("<slug:slug>/", views.detail, name="detail"),
    path("<slug:slug>/modifier/", views.edit, name="edit"),
    path("<slug:slug>/supprimer/", views.delete, name="delete"),
    path("<slug:slug>/bravo/", views.applaud, name="applaud"),
    path("<slug:slug>/retours/", views.pin_create, name="pin_create"),
]
