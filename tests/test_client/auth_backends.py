from django.contrib.auth.backends import ModelBackend


class TestClientBackend(ModelBackend):
    pass


class BackendWithoutGetUserMethod(object):
    pass
