from django.contrib.auth.models import User, check_password

class ModelBackend:
    """
    Authenticate against django.contrib.auth.models.User
    """
    # TODO: Model, login attribute name and password attribute name should be
    # configurable.
    def authenticate(self, username=None, password=None):
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
