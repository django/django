import inspect
import re
import warnings

from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.middleware.csrf import rotate_token
from django.utils.crypto import constant_time_compare
from django.utils.deprecation import RemovedInDjango61Warning
from django.utils.module_loading import import_string
from django.views.decorators.debug import sensitive_variables

from .signals import user_logged_in, user_logged_out, user_login_failed

SESSION_KEY = "_auth_user_id"
BACKEND_SESSION_KEY = "_auth_user_backend"
HASH_SESSION_KEY = "_auth_user_hash"
REDIRECT_FIELD_NAME = "next"


def load_backend(path):
    return import_string(path)()


def _get_backends(return_tuples=False):
    backends = []
    for backend_path in settings.AUTHENTICATION_BACKENDS:
        backend = load_backend(backend_path)
        backends.append((backend, backend_path) if return_tuples else backend)
    if not backends:
        raise ImproperlyConfigured(
            "No authentication backends have been defined. Does "
            "AUTHENTICATION_BACKENDS contain anything?"
        )
    return backends


def get_backends():
    return _get_backends(return_tuples=False)


def _get_compatible_backends(request, **credentials):
    for backend, backend_path in _get_backends(return_tuples=True):
        backend_signature = inspect.signature(backend.authenticate)
        try:
            backend_signature.bind(request, **credentials)
        except TypeError:
            # This backend doesn't accept these credentials as arguments. Try
            # the next one.
            continue
        yield backend, backend_path


def _get_backend_from_user(user, backend=None):
    try:
        backend = backend or user.backend
    except AttributeError:
        backends = _get_backends(return_tuples=True)
        if len(backends) == 1:
            _, backend = backends[0]
        else:
            raise ValueError(
                "You have multiple authentication backends configured and "
                "therefore must provide the `backend` argument or set the "
                "`backend` attribute on the user."
            )
    else:
        if not isinstance(backend, str):
            raise TypeError(
                "backend must be a dotted import path string (got %r)." % backend
            )
    return backend


@sensitive_variables("credentials")
def _clean_credentials(credentials):
    """
    Clean a dictionary of credentials of potentially sensitive info before
    sending to less secure functions.

    Not comprehensive - intended for user_login_failed signal
    """
    SENSITIVE_CREDENTIALS = re.compile("api|token|key|secret|password|signature", re.I)
    CLEANSED_SUBSTITUTE = "********************"
    for key in credentials:
        if SENSITIVE_CREDENTIALS.search(key):
            credentials[key] = CLEANSED_SUBSTITUTE
    return credentials


def _get_user_session_key(request):
    # This value in the session is always serialized to a string, so we need
    # to convert it back to Python whenever we access it.
    return get_user_model()._meta.pk.to_python(request.session[SESSION_KEY])


async def _aget_user_session_key(request):
    # This value in the session is always serialized to a string, so we need
    # to convert it back to Python whenever we access it.
    session_key = await request.session.aget(SESSION_KEY)
    if session_key is None:
        raise KeyError()
    return get_user_model()._meta.pk.to_python(session_key)


@sensitive_variables("credentials")
def authenticate(request=None, **credentials):
    """
    If the given credentials are valid, return a User object.
    """
    for backend, backend_path in _get_compatible_backends(request, **credentials):
        try:
            user = backend.authenticate(request, **credentials)
        except PermissionDenied:
            # This backend says to stop in our tracks - this user should not be
            # allowed in at all.
            break
        if user is None:
            continue
        # Annotate the user object with the path of the backend.
        user.backend = backend_path
        return user

    # The credentials supplied are invalid to all backends, fire signal
    user_login_failed.send(
        sender=__name__, credentials=_clean_credentials(credentials), request=request
    )


@sensitive_variables("credentials")
async def aauthenticate(request=None, **credentials):
    """See authenticate()."""
    for backend, backend_path in _get_compatible_backends(request, **credentials):
        try:
            user = await backend.aauthenticate(request, **credentials)
        except PermissionDenied:
            # This backend says to stop in our tracks - this user should not be
            # allowed in at all.
            break
        if user is None:
            continue
        # Annotate the user object with the path of the backend.
        user.backend = backend_path
        return user

    # The credentials supplied are invalid to all backends, fire signal.
    await user_login_failed.asend(
        sender=__name__, credentials=_clean_credentials(credentials), request=request
    )


def login(request, user, backend=None):
    """
    Persist a user id and a backend in the request. This way a user doesn't
    have to reauthenticate on every request. Note that data set during
    the anonymous session is retained when the user logs in.
    """
    # RemovedInDjango61Warning: When the deprecation ends, replace with:
    # session_auth_hash = user.get_session_auth_hash()
    session_auth_hash = ""
    # RemovedInDjango61Warning.
    if user is None:
        user = request.user
        warnings.warn(
            "Fallback to request.user when user is None will be removed.",
            RemovedInDjango61Warning,
            stacklevel=2,
        )

    # RemovedInDjango61Warning.
    if hasattr(user, "get_session_auth_hash"):
        session_auth_hash = user.get_session_auth_hash()

    if SESSION_KEY in request.session:
        if _get_user_session_key(request) != user.pk or (
            session_auth_hash
            and not constant_time_compare(
                request.session.get(HASH_SESSION_KEY, ""), session_auth_hash
            )
        ):
            # To avoid reusing another user's session, create a new, empty
            # session if the existing session corresponds to a different
            # authenticated user.
            request.session.flush()
    else:
        request.session.cycle_key()

    backend = _get_backend_from_user(user=user, backend=backend)

    request.session[SESSION_KEY] = user._meta.pk.value_to_string(user)
    request.session[BACKEND_SESSION_KEY] = backend
    request.session[HASH_SESSION_KEY] = session_auth_hash
    if hasattr(request, "user"):
        request.user = user
    rotate_token(request)
    user_logged_in.send(sender=user.__class__, request=request, user=user)


async def alogin(request, user, backend=None):
    """See login()."""
    # RemovedInDjango61Warning: When the deprecation ends, replace with:
    # session_auth_hash = user.get_session_auth_hash()
    session_auth_hash = ""
    # RemovedInDjango61Warning.
    if user is None:
        warnings.warn(
            "Fallback to request.auser() when user is None will be removed.",
            RemovedInDjango61Warning,
            stacklevel=2,
        )
        user = await request.auser()
    # RemovedInDjango61Warning.
    if hasattr(user, "get_session_auth_hash"):
        session_auth_hash = user.get_session_auth_hash()

    if await request.session.ahas_key(SESSION_KEY):
        if await _aget_user_session_key(request) != user.pk or (
            session_auth_hash
            and not constant_time_compare(
                await request.session.aget(HASH_SESSION_KEY, ""),
                session_auth_hash,
            )
        ):
            # To avoid reusing another user's session, create a new, empty
            # session if the existing session corresponds to a different
            # authenticated user.
            await request.session.aflush()
    else:
        await request.session.acycle_key()

    backend = _get_backend_from_user(user=user, backend=backend)

    await request.session.aset(SESSION_KEY, user._meta.pk.value_to_string(user))
    await request.session.aset(BACKEND_SESSION_KEY, backend)
    await request.session.aset(HASH_SESSION_KEY, session_auth_hash)
    if hasattr(request, "user"):
        request.user = user
    rotate_token(request)
    await user_logged_in.asend(sender=user.__class__, request=request, user=user)


def logout(request):
    """
    Remove the authenticated user's ID from the request and flush their session
    data.
    """
    # Dispatch the signal before the user is logged out so the receivers have a
    # chance to find out *who* logged out.
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", True):
        user = None
    user_logged_out.send(sender=user.__class__, request=request, user=user)
    request.session.flush()
    if hasattr(request, "user"):
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()


async def alogout(request):
    """See logout()."""
    # Dispatch the signal before the user is logged out so the receivers have a
    # chance to find out *who* logged out.
    user = getattr(request, "auser", None)
    if user is not None:
        user = await user()
    if not getattr(user, "is_authenticated", True):
        user = None
    await user_logged_out.asend(sender=user.__class__, request=request, user=user)
    await request.session.aflush()
    if hasattr(request, "user"):
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()


def get_user_model():
    """
    Return the User model that is active in this project.
    """
    try:
        return django_apps.get_model(settings.AUTH_USER_MODEL, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured(
            "AUTH_USER_MODEL must be of the form 'app_label.model_name'"
        )
    except LookupError:
        raise ImproperlyConfigured(
            "AUTH_USER_MODEL refers to model '%s' that has not been installed"
            % settings.AUTH_USER_MODEL
        )


def get_user(request):
    """
    Return the user model instance associated with the given request session.
    If no user is retrieved, return an instance of `AnonymousUser`.
    """
    from .models import AnonymousUser

    user = None
    try:
        user_id = _get_user_session_key(request)
        backend_path = request.session[BACKEND_SESSION_KEY]
    except KeyError:
        pass
    else:
        if backend_path in settings.AUTHENTICATION_BACKENDS:
            backend = load_backend(backend_path)
            user = backend.get_user(user_id)
            # Verify the session
            if hasattr(user, "get_session_auth_hash"):
                session_hash = request.session.get(HASH_SESSION_KEY)
                if not session_hash:
                    session_hash_verified = False
                else:
                    session_auth_hash = user.get_session_auth_hash()
                    session_hash_verified = constant_time_compare(
                        session_hash, session_auth_hash
                    )
                if not session_hash_verified:
                    # If the current secret does not verify the session, try
                    # with the fallback secrets and stop when a matching one is
                    # found.
                    if session_hash and any(
                        constant_time_compare(session_hash, fallback_auth_hash)
                        for fallback_auth_hash in user.get_session_auth_fallback_hash()
                    ):
                        request.session.cycle_key()
                        request.session[HASH_SESSION_KEY] = session_auth_hash
                    else:
                        request.session.flush()
                        user = None

    return user or AnonymousUser()


async def aget_user(request):
    """See get_user()."""
    from .models import AnonymousUser

    user = None
    try:
        user_id = await _aget_user_session_key(request)
        backend_path = await request.session.aget(BACKEND_SESSION_KEY)
    except KeyError:
        pass
    else:
        if backend_path in settings.AUTHENTICATION_BACKENDS:
            backend = load_backend(backend_path)
            user = await backend.aget_user(user_id)
            # Verify the session
            if hasattr(user, "get_session_auth_hash"):
                session_hash = await request.session.aget(HASH_SESSION_KEY)
                if not session_hash:
                    session_hash_verified = False
                else:
                    session_auth_hash = user.get_session_auth_hash()
                    session_hash_verified = session_hash and constant_time_compare(
                        session_hash, user.get_session_auth_hash()
                    )
                if not session_hash_verified:
                    # If the current secret does not verify the session, try
                    # with the fallback secrets and stop when a matching one is
                    # found.
                    if session_hash and any(
                        constant_time_compare(session_hash, fallback_auth_hash)
                        for fallback_auth_hash in user.get_session_auth_fallback_hash()
                    ):
                        await request.session.acycle_key()
                        await request.session.aset(HASH_SESSION_KEY, session_auth_hash)
                    else:
                        await request.session.aflush()
                        user = None

    return user or AnonymousUser()


def get_permission_codename(action, opts):
    """
    Return the codename of the permission for the specified action.
    """
    return "%s_%s" % (action, opts.model_name)


def update_session_auth_hash(request, user):
    """
    Updating a user's password logs out all sessions for the user.

    Take the current request and the updated user object from which the new
    session hash will be derived and update the session hash appropriately to
    prevent a password change from logging out the session from which the
    password was changed.
    """
    request.session.cycle_key()
    if hasattr(user, "get_session_auth_hash") and request.user == user:
        request.session[HASH_SESSION_KEY] = user.get_session_auth_hash()


async def aupdate_session_auth_hash(request, user):
    """See update_session_auth_hash()."""
    await request.session.acycle_key()
    if hasattr(user, "get_session_auth_hash") and request.user == user:
        await request.session.aset(HASH_SESSION_KEY, user.get_session_auth_hash())
