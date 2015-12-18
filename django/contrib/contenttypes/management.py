from django.apps import apps
from django.db import DEFAULT_DB_ALIAS, migrations, router, transaction
from django.db.utils import IntegrityError
from django.utils import six
from django.utils.six.moves import input


class RenameContentType(migrations.RunPython):
    def __init__(self, app_label, old_name, new_name):
        self.app_label = app_label
        self.old_name = old_name
        self.new_name = new_name
        super(RenameContentType, self).__init__(self.rename_forward, self.rename_backward)

    def _rename(self, apps, old_name, new_name):
        ContentType = apps.get_model('contenttypes', 'ContentType')
        try:
            content_type = ContentType.objects.get_by_natural_key(self.app_label, old_name.lower())
        except ContentType.DoesNotExist:
            pass
        else:
            content_type.model = new_name.lower()
            using = router.db_for_write(ContentType, instance=content_type)
            try:
                with transaction.atomic(using=using):
                    content_type.save(update_fields={'model'})
            except IntegrityError:
                # Gracefully fallback if a stale content type causes a conflict.
                pass

    def rename_forward(self, apps, schema_editor):
        self._rename(apps, self.old_name, self.new_name)

    def rename_backward(self, apps, schema_editor):
        self._rename(apps, self.new_name, self.old_name)


def rename_contenttypes(plan=None, **kwargs):
    """
    Inserts a `RenameContentType` operation after every planned
    `RenameModel` operation.
    """
    if plan is None:
        plan = []
    for migration, _backward in plan:
        inserts = []
        for index, operation in enumerate(migration.operations):
            if isinstance(operation, migrations.RenameModel):
                operation = RenameContentType(migration.app_label, operation.old_name, operation.new_name)
                inserts.append((index + 1, operation))
        for inserted, (index, operation) in enumerate(inserts):
            migration.operations.insert(inserted + index, operation)


def update_contenttypes(app_config, verbosity=2, interactive=True, using=DEFAULT_DB_ALIAS, **kwargs):
    """
    Creates content types for models in the given app, removing any model
    entries that no longer have a matching model class.
    """
    if not app_config.models_module:
        return

    try:
        ContentType = apps.get_model('contenttypes', 'ContentType')
    except LookupError:
        return

    if not router.allow_migrate_model(using, ContentType):
        return

    ContentType.objects.clear_cache()

    app_label = app_config.label

    app_models = {
        model._meta.model_name: model
        for model in app_config.get_models()}

    if not app_models:
        return

    # Get all the content types
    content_types = {
        ct.model: ct
        for ct in ContentType.objects.using(using).filter(app_label=app_label)
    }
    to_remove = [
        ct
        for (model_name, ct) in six.iteritems(content_types)
        if model_name not in app_models
    ]

    cts = [
        ContentType(
            app_label=app_label,
            model=model_name,
        )
        for (model_name, model) in six.iteritems(app_models)
        if model_name not in content_types
    ]
    ContentType.objects.using(using).bulk_create(cts)
    if verbosity >= 2:
        for ct in cts:
            print("Adding content type '%s | %s'" % (ct.app_label, ct.model))

    # Confirm that the content type is stale before deletion.
    if to_remove:
        if interactive:
            content_type_display = '\n'.join(
                '    %s | %s' % (ct.app_label, ct.model)
                for ct in to_remove
            )
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
