import datetime
from django.core.exceptions import ImproperlyConfigured

SESSION_KEY = '_auth_user_id'
BACKEND_SESSION_KEY = '_auth_user_backend'
REDIRECT_FIELD_NAME = 'next'

def load_backend(path):
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]
    try:
        mod = __import__(module, {}, {}, [attr])
    except ImportError, e:
        raise ImproperlyConfigured, 'Error importing authentication backend %s: "%s"' % (module, e)
    try:
        cls = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured, 'Module "%s" does not define a "%s" authentication backend' % (module, attr)
    return cls()

def get_backends():
    from django.conf import settings
    backends = []
    for backend_path in settings.AUTHENTICATION_BACKENDS:
        backends.append(load_backend(backend_path))
    return backends

def authenticate(**credentials):
    """
    If the given credentials are valid, return a User object.
    """
    for backend in get_backends():
        try:
            user = backend.authenticate(**credentials)
        except TypeError:
            # This backend doesn't accept these credentials as arguments. Try the next one.
            continue
        if user is None:
            continue
        # Annotate the user object with the path of the backend.
        user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
        return user

def login(request, user):
    """
    Persist a user id and a backend in the request. This way a user doesn't
    have to reauthenticate on every request.
    """
    if user is None:
        user = request.user
    # TODO: It would be nice to support different login methods, like signed cookies.
    user.last_login = datetime.datetime.now()
    user.save()
    request.session[SESSION_KEY] = user.id
    request.session[BACKEND_SESSION_KEY] = user.backend

def logout(request):
    """
    Remove the authenticated user's ID from the request.
    """
    try:
        del request.session[SESSION_KEY]
    except KeyError:
        pass
    try:
        del request.session[BACKEND_SESSION_KEY]
    except KeyError:
        pass

def get_user(request):
    from django.contrib.auth.models import AnonymousUser
    try:
        user_id = request.session[SESSION_KEY]
        backend_path = request.session[BACKEND_SESSION_KEY]
        backend = load_backend(backend_path)
        user = backend.get_user(user_id) or AnonymousUser()
    except KeyError:
        user = AnonymousUser()
    return user
