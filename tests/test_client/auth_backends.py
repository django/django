from django.contrib.auth.backends import BaseBackend, ModelBackend


class TestClientBackend(ModelBackend):
    pass


class BackendWithoutGetUserMethod:
    pass


class PermissionOnlyBackend(BaseBackend):
    """This class inherits from BaseBackend but does not implement get_user."""

    pass
