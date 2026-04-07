from django.contrib.auth.backends import BaseBackend, ModelBackend


class TestClientBackend(ModelBackend):
    pass


class BackendWithoutGetUserMethod:
    pass


class PermissionOnlyBackend(BaseBackend):
    pass
