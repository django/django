"""
Creates permissions for all installed apps that need permissions.
"""
import getpass
import locale
import unicodedata
from django.contrib.auth import models as auth_app
from django.db.models import get_models, signals
from django.contrib.auth.models import User


def _get_permission_codename(action, opts):
    return u'%s_%s' % (action, opts.object_name.lower())


def _get_all_permissions(opts):
    "Returns (codename, name) for all permissions in the given opts."
    perms = []
    for action in ('add', 'change', 'delete'):
        perms.append((_get_permission_codename(action, opts), u'Can %s %s' % (action, opts.verbose_name_raw)))
    return perms + list(opts.permissions)


def create_permissions(app, created_models, verbosity, **kwargs):
    from django.contrib.contenttypes.models import ContentType

    app_models = get_models(app)

    # This will hold the permissions we're looking for as
    # (content_type, (codename, name))
    searched_perms = list()
    # The codenames and ctypes that should exist.
    ctypes = set()
    for klass in app_models:
        ctype = ContentType.objects.get_for_model(klass)
        ctypes.add(ctype)
        for perm in _get_all_permissions(klass._meta):
            searched_perms.append((ctype, perm))

    # Find all the Permissions that have a context_type for a model we're
    # looking for.  We don't need to check for codenames since we already have
    # a list of the ones we're going to create.
    all_perms = set(auth_app.Permission.objects.filter(
        content_type__in=ctypes,
    ).values_list(
        "content_type", "codename"
    ))

    objs = [
        auth_app.Permission(codename=codename, name=name, content_type=ctype)
        for ctype, (codename, name) in searched_perms
        if (ctype.pk, codename) not in all_perms
    ]
    auth_app.Permission.objects.bulk_create(objs)
    if verbosity >= 2:
        for obj in objs:
            print "Adding permission '%s'" % obj


def create_superuser(app, created_models, verbosity, db, **kwargs):
    from django.core.management import call_command

    if auth_app.User in created_models and kwargs.get('interactive', True):
        msg = ("\nYou just installed Django's auth system, which means you "
            "don't have any superusers defined.\nWould you like to create one "
            "now? (yes/no): ")
        confirm = raw_input(msg)
        while 1:
            if confirm not in ('yes', 'no'):
                confirm = raw_input('Please enter either "yes" or "no": ')
                continue
            if confirm == 'yes':
                call_command("createsuperuser", interactive=True, database=db)
            break


def get_system_username():
    """
    Try to determine the current system user's username.

    :returns: The username as a unicode string, or an empty string if the
        username could not be determined.
    """
    try:
        return getpass.getuser().decode(locale.getdefaultlocale()[1])
    except (ImportError, KeyError, UnicodeDecodeError):
        # KeyError will be raised by os.getpwuid() (called by getuser())
        # if there is no corresponding entry in the /etc/passwd file
        # (a very restricted chroot environment, for example).
        # UnicodeDecodeError - preventive treatment for non-latin Windows.
        return u''


def get_default_username(check_db=True):
    """
    Try to determine the current system user's username to use as a default.

    :param check_db: If ``True``, requires that the username does not match an
        existing ``auth.User`` (otherwise returns an empty string).
    :returns: The username, or an empty string if no username can be
        determined.
    """
    from django.contrib.auth.management.commands.createsuperuser import (
        RE_VALID_USERNAME)
    default_username = get_system_username()
    try:
        default_username = unicodedata.normalize('NFKD', default_username)\
            .encode('ascii', 'ignore').replace(' ', '').lower()
    except UnicodeDecodeError:
        return ''
    if not RE_VALID_USERNAME.match(default_username):
        return ''
    # Don't return the default username if it is already taken.
    if check_db and default_username:
        try:
            User.objects.get(username=default_username)
        except User.DoesNotExist:
            pass
        else:
            return ''
    return default_username


signals.post_syncdb.connect(create_permissions,
    dispatch_uid = "django.contrib.auth.management.create_permissions")
signals.post_syncdb.connect(create_superuser,
    sender=auth_app, dispatch_uid = "django.contrib.auth.management.create_superuser")
