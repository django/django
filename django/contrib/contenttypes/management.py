from django.contrib.contenttypes.models import ContentType
from django.db.models import get_apps, get_models, signals
from django.utils.encoding import smart_unicode

def update_contenttypes(app, created_models, verbosity=2, **kwargs):
    """
    Creates content types for models in the given app, removing any model
    entries that no longer have a matching model class.
    """
    db = kwargs['db']
    ContentType.objects.clear_cache()
    content_types = list(ContentType.objects.using(db).filter(app_label=app.__name__.split('.')[-2]))
    app_models = get_models(app)
    if not app_models:
        return
    for klass in app_models:
        opts = klass._meta
        try:
            ct = ContentType.objects.using(db).get(app_label=opts.app_label,
                                                   model=opts.object_name.lower())
            content_types.remove(ct)
        except ContentType.DoesNotExist:
            ct = ContentType(name=smart_unicode(opts.verbose_name_raw),
                app_label=opts.app_label, model=opts.object_name.lower())
            ct.save(using=db)
            if verbosity >= 2:
                print "Adding content type '%s | %s'" % (ct.app_label, ct.model)
    # The presence of any remaining content types means the supplied app has an
    # undefined model and can safely be removed, which cascades to also remove
    # related permissions.
    for ct in content_types:
        if verbosity >= 2:
            print "Deleting stale content type '%s | %s'" % (ct.app_label, ct.model)
        ct.delete()

def update_all_contenttypes(verbosity=2):
    for app in get_apps():
        update_contenttypes(app, None, verbosity)

signals.post_syncdb.connect(update_contenttypes)

if __name__ == "__main__":
    update_all_contenttypes()
