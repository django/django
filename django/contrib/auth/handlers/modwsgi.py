from django import db
from django.contrib import auth

UserModel = auth.get_user_model()


def _get_user(username):
    """
    Return the UserModel instance for `username`.

    If no matching user exists, or if the user is inactive, return None, in
    which case the default password hasher is run to mitigate timing attacks.
    """
    try:
        user = UserModel._default_manager.get_by_natural_key(username)
    except UserModel.DoesNotExist:
        user = None
    else:
        if not user.is_active:
            user = None

    if user is None:
        # Run the default password hasher once to reduce the timing difference
        # between existing/active and nonexistent/inactive users (#20760).
        UserModel().set_password("")

    return user


def check_password(environ, username, password):
    """
    Authenticate against Django's auth database.

    mod_wsgi docs specify None, True, False as return value depending
    on whether the user exists and authenticates.

    Return None if the user does not exist, return False if the user exists but
    password is not correct, and return True otherwise.

    """
    # db connection state is managed similarly to the wsgi handler
    # as mod_wsgi may call these functions outside of a request/response cycle
    db.reset_queries()
    try:
        user = _get_user(username)
        if user:
            return user.check_password(password)
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
        if not user.is_active:
            return []
        return [group.name.encode() for group in user.groups.all()]
    finally:
        db.close_old_connections()
