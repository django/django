"""
Creates permissions for all installed apps that need permissions.
"""

from django.db.models import get_models, signals
from django.contrib.auth import models as auth_app

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
    from django.contrib.auth.models import Permission
    app_models = get_models(app)
    if not app_models:
        return
    for klass in app_models:
        ctype = ContentType.objects.get_for_model(klass)
        for codename, name in _get_all_permissions(klass._meta):
            p, created = Permission.objects.get_or_create(codename=codename, content_type__pk=ctype.id,
                defaults={'name': name, 'content_type': ctype})
            if created and verbosity >= 2:
                print "Adding permission '%s'" % p

def create_superuser(app, created_models, verbosity, **kwargs):
    from django.contrib.auth.models import User
    from django.core.management import call_command
    if User in created_models and kwargs.get('interactive', True):
        msg = "\nYou just installed Django's auth system, which means you don't have " \
                "any superusers defined.\nWould you like to create one now? (yes/no): "
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
