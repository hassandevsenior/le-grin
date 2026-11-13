from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Permet de se connecter avec son pseudo ou son adresse e-mail."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None or password is None:
            return None
        lookup = {"email__iexact": username} if "@" in username else {"username__iexact": username}
        try:
            user = User.objects.get(**lookup)
        except User.DoesNotExist:
            # Même coût de calcul qu'un vrai essai, pour ne pas révéler quels comptes existent.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
