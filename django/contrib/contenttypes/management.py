"""
Creates content types for all installed models.
"""

from django.dispatch import dispatcher
from django.db.models import get_apps, get_models, signals

def create_contenttypes(app, created_models, verbosity=2):
    from django.contrib.contenttypes.models import ContentType
    ContentType.objects.clear_cache()
    app_models = get_models(app)
    if not app_models:
        return
    for klass in app_models:
        opts = klass._meta
        try:
            ContentType.objects.get(app_label=opts.app_label,
                model=opts.object_name.lower())
        except ContentType.DoesNotExist:
            ct = ContentType(name=str(opts.verbose_name),
                app_label=opts.app_label, model=opts.object_name.lower())
            ct.save()
            if verbosity >= 2:
                print "Adding content type '%s | %s'" % (ct.app_label, ct.model)

def create_all_contenttypes(verbosity=2):
    for app in get_apps():
        create_contenttypes(app, None, verbosity)

dispatcher.connect(create_contenttypes, signal=signals.post_syncdb)

if __name__ == "__main__":
    create_all_contenttypes()
