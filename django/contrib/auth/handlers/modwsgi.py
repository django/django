from django.contrib.auth.models import User
from django import db
from django.utils.encoding import force_bytes


def check_password(environ, username, password):
    """
    Authenticates against Django's auth database

    mod_wsgi docs specify None, True, False as return value depending
    on whether the user exists and authenticates.
    """

    # db connection state is managed similarly to the wsgi handler
    # as mod_wsgi may call these functions outside of a request/response cycle
    db.reset_queries()

    try:
        try:
            user = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            return None
        return user.check_password(password)
    finally:
        db.close_connection()


def groups_for_user(environ, username):
    """
    Authorizes a user based on groups
    """

    db.reset_queries()

    try:
        try:
            user = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            return []

        return [force_bytes(group.name) for group in user.groups.all()]
    finally:
        db.close_connection()
