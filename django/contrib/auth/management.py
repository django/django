"""
Creates permissions for all installed apps that need permissions.
"""

from django.dispatch import dispatcher
from django.db.models import get_models, signals
from django.contrib.auth import models as auth_app

def _get_permission_codename(action, opts):
    return '%s_%s' % (action, opts.object_name.lower())

def _get_all_permissions(opts):
    "Returns (codename, name) for all permissions in the given opts."
    perms = []
    for action in ('add', 'change', 'delete'):
        perms.append((_get_permission_codename(action, opts), 'Can %s %s' % (action, opts.verbose_name)))
    return perms + list(opts.permissions)

def create_permissions(app, created_models):
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission
    app_models = get_models(app)
    if not app_models:
        return
    for klass in app_models:
        if not klass._meta.admin:
            continue
        ctype = ContentType.objects.get_for_model(klass)
        for codename, name in _get_all_permissions(klass._meta):
            try:
                Permission.objects.get(name=name, codename=codename, content_type__pk=ctype.id)
            except Permission.DoesNotExist:
                p = Permission(name=name, codename=codename, content_type=ctype)
                p.save()
                print "Adding permission '%r'" % p

def create_superuser(app, created_models):
    from django.contrib.auth.models import User
    from django.contrib.auth.create_superuser import createsuperuser as do_create
    if User in created_models:
        msg = "\nYou just installed Django's auth system, which means you don't have " \
                "any superusers defined.\nWould you like to create one now? (yes/no): "
        confirm = raw_input(msg)
        while 1:
            if confirm not in ('yes', 'no'):
                confirm = raw_input('Please enter either "yes" or "no": ')
                continue
            if confirm == 'yes':
                do_create()
            break

dispatcher.connect(create_permissions, signal=signals.post_syncdb)
dispatcher.connect(create_superuser, sender=auth_app, signal=signals.post_syncdb)
