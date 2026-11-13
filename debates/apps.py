from django.apps import AppConfig


class DebatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "debates"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        from .services import publish_pending

        def publish_on_login(sender, request, user, **kwargs):
            # Un membre qui a voté avant de se connecter retrouve son vote publié.
            if request is not None:
                publish_pending(request, user)

        user_logged_in.connect(publish_on_login, weak=False, dispatch_uid="publish_pending_stance")
