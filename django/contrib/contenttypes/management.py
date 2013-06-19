from django.contrib.contenttypes.models import ContentType
from django.db import DEFAULT_DB_ALIAS, router
from django.db.models import get_apps, get_model, get_models, signals, UnavailableApp
from django.utils.encoding import smart_text
from django.utils import six
from django.utils.six.moves import input


def update_contenttypes(app, created_models, verbosity=2, db=DEFAULT_DB_ALIAS, **kwargs):
    """
    Creates content types for models in the given app, removing any model
    entries that no longer have a matching model class.
    """
    try:
        get_model('contenttypes', 'ContentType')
    except UnavailableApp:
        return

    if not router.allow_syncdb(db, ContentType):
        return

    ContentType.objects.clear_cache()
    app_models = get_models(app)
    if not app_models:
        return
    # They all have the same app_label, get the first one.
    app_label = app_models[0]._meta.app_label
    app_models = dict(
        (model._meta.model_name, model)
        for model in app_models
    )

    # Get all the content types
    content_types = dict(
        (ct.model, ct)
        for ct in ContentType.objects.using(db).filter(app_label=app_label)
    )
    to_remove = [
        ct
        for (model_name, ct) in six.iteritems(content_types)
        if model_name not in app_models
    ]

    cts = [
        ContentType(
            name=smart_text(model._meta.verbose_name_raw),
            app_label=app_label,
            model=model_name,
        )
        for (model_name, model) in six.iteritems(app_models)
        if model_name not in content_types
    ]
    ContentType.objects.using(db).bulk_create(cts)
    if verbosity >= 2:
        for ct in cts:
            print("Adding content type '%s | %s'" % (ct.app_label, ct.model))

    # Confirm that the content type is stale before deletion.
    if to_remove:
        if kwargs.get('interactive', False):
            content_type_display = '\n'.join([
                '    %s | %s' % (ct.app_label, ct.model)
                for ct in to_remove
            ])
            ok_to_delete = input("""The following content types are stale and need to be deleted:

%s

Any objects related to these content types by a foreign key will also
be deleted. Are you sure you want to delete these content types?
If you're unsure, answer 'no'.

    Type 'yes' to continue, or 'no' to cancel: """ % content_type_display)
        else:
            ok_to_delete = False

        if ok_to_delete == 'yes':
            for ct in to_remove:
                if verbosity >= 2:
                    print("Deleting stale content type '%s | %s'" % (ct.app_label, ct.model))
                ct.delete()
        else:
            if verbosity >= 2:
                print("Stale content types remain.")


def update_all_contenttypes(verbosity=2, **kwargs):
    for app in get_apps():
        update_contenttypes(app, None, verbosity, **kwargs)

signals.post_syncdb.connect(update_contenttypes)

if __name__ == "__main__":
    update_all_contenttypes()
