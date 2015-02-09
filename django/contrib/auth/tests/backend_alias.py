# For testing that auth backends can be referenced using a convenience import
from django.contrib.auth.tests.test_auth_backends import ImportedModelBackend

__all__ = ['ImportedModelBackend']
