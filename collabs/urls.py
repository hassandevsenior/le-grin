from django.urls import path

from . import views

app_name = "collabs"

urlpatterns = [
    path("", views.request_list, name="list"),
    path("nouveau/", views.create, name="create"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/s-engager/", views.commit, name="commit"),
    path("<int:pk>/se-liberer/", views.release, name="release"),
    path("<int:pk>/tenu/<int:commitment_id>/", views.mark_kept, name="kept"),
    path("<int:pk>/etat/", views.toggle_open, name="toggle"),
    path("<int:pk>/point/", views.add_update, name="update"),
]
