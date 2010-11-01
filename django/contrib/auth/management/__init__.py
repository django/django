"""
Creates permissions for all installed apps that need permissions.
"""

from django.contrib.auth import models as auth_app
from django.db.models import get_models, signals


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
    searched_perms = set()
    # The codenames and ctypes that should exist.
    ctypes = set()
    codenames = set()
    for klass in app_models:
        ctype = ContentType.objects.get_for_model(klass)
        ctypes.add(ctype)
        for perm in _get_all_permissions(klass._meta):
            codenames.add(perm[0])
            searched_perms.add((ctype, perm))

    # Find all the Permissions that a) have a content_type for a model we're
    # looking for, and b) have a codename we're looking for. It doesn't need to
    # have both, we have a list of exactly what we want, and it's faster to
    # write the query with fewer conditions.
    all_perms = set(auth_app.Permission.objects.filter(
        content_type__in=ctypes,
        codename__in=codenames
    ).values_list(
        "content_type", "codename"
    ))

    for ctype, (codename, name) in searched_perms:
        # If the permissions exists, move on.
        if (ctype.pk, codename) in all_perms:
            continue
        p = auth_app.Permission.objects.create(
            codename=codename,
            name=name,
            content_type=ctype
        )
        if verbosity >= 2:
            print "Adding permission '%s'" % p


def create_superuser(app, created_models, verbosity, **kwargs):
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
                call_command("createsuperuser", interactive=True)
            break

signals.post_syncdb.connect(create_permissions,
    dispatch_uid = "django.contrib.auth.management.create_permissions")
signals.post_syncdb.connect(create_superuser,
    sender=auth_app, dispatch_uid = "django.contrib.auth.management.create_superuser")
