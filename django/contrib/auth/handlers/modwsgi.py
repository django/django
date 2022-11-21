from django import db
from django.contrib import auth

UserModel = auth.get_user_model()


def check_password(environ, username, password):
    """
    Authenticate against Django's auth database.

    mod_wsgi docs specify None, True, False as return value depending
    on whether the user exists and authenticates.
    """
    # db connection state is managed similarly to the wsgi handler
    # as mod_wsgi may call these functions outside of a request/response cycle
    db.reset_queries()
    try:
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            return None
        return user.check_password(password) if user.is_active else None
    finally:
        db.close_old_connections()


def groups_for_user(environ, username):
    """
    Authorize a user based on groups
    """
    db.reset_queries()
    try:
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            return []
        return (
            [group.name.encode() for group in user.groups.all()]
            if user.is_active
            else []
        )

    finally:
        db.close_old_connections()
