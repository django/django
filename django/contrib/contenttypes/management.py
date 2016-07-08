from django.apps import apps as global_apps
from django.db import DEFAULT_DB_ALIAS, migrations, router, transaction
from django.db.models.deletion import Collector
from django.db.utils import IntegrityError
from django.utils import six
from django.utils.six.moves import input


class RenameContentType(migrations.RunPython):
    def __init__(self, app_label, old_model, new_model):
        self.app_label = app_label
        self.old_model = old_model
        self.new_model = new_model
        super(RenameContentType, self).__init__(self.rename_forward, self.rename_backward)

    def _rename(self, apps, schema_editor, old_model, new_model):
        ContentType = apps.get_model('contenttypes', 'ContentType')
        db = schema_editor.connection.alias
        if not router.allow_migrate_model(db, ContentType):
            return

        try:
            content_type = ContentType.objects.db_manager(db).get_by_natural_key(self.app_label, old_model)
        except ContentType.DoesNotExist:
            pass
        else:
            content_type.model = new_model
            try:
                with transaction.atomic(using=db):
                    content_type.save(update_fields={'model'})
            except IntegrityError:
                # Gracefully fallback if a stale content type causes a
                # conflict as update_contenttypes will take care of asking the
                # user what should be done next.
                content_type.model = old_model
            else:
                # Clear the cache as the `get_by_natual_key()` call will cache
                # the renamed ContentType instance by its old model name.
                ContentType.objects.clear_cache()

    def rename_forward(self, apps, schema_editor):
        self._rename(apps, schema_editor, self.old_model, self.new_model)

    def rename_backward(self, apps, schema_editor):
        self._rename(apps, schema_editor, self.new_model, self.old_model)


def inject_rename_contenttypes_operations(plan=None, apps=global_apps, using=DEFAULT_DB_ALIAS, **kwargs):
    """
    Insert a `RenameContentType` operation after every planned `RenameModel`
    operation.
    """
    if plan is None:
        return

    # Determine whether or not the ContentType model is available.
    try:
        ContentType = apps.get_model('contenttypes', 'ContentType')
    except LookupError:
        available = False
    else:
        if not router.allow_migrate_model(using, ContentType):
            return
        available = True

    for migration, backward in plan:
        if ((migration.app_label, migration.name) == ('contenttypes', '0001_initial')):
            # There's no point in going forward if the initial contenttypes
            # migration is unapplied as the ContentType model will be
            # unavailable from this point.
            if backward:
                break
            else:
                available = True
                continue
        # The ContentType model is not available yet.
        if not available:
            continue
        inserts = []
        for index, operation in enumerate(migration.operations):
            if isinstance(operation, migrations.RenameModel):
                operation = RenameContentType(
                    migration.app_label, operation.old_name_lower, operation.new_name_lower
                )
                inserts.append((index + 1, operation))
        for inserted, (index, operation) in enumerate(inserts):
            migration.operations.insert(inserted + index, operation)


def update_contenttypes(app_config, verbosity=2, interactive=True, using=DEFAULT_DB_ALIAS, apps=global_apps, **kwargs):
    """
    Creates content types for models in the given app, removing any model
    entries that no longer have a matching model class.
    """
    if not app_config.models_module:
        return

    app_label = app_config.label
    try:
        app_config = apps.get_app_config(app_label)
        ContentType = apps.get_model('contenttypes', 'ContentType')
    except LookupError:
        return

    if not router.allow_migrate_model(using, ContentType):
        return

    ContentType.objects.clear_cache()
    # Always clear the global content types cache.
    if apps is not global_apps:
        global_apps.get_model('contenttypes', 'ContentType').objects.clear_cache()

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
    using = router.db_for_write(ContentType)
    if to_remove:
        if interactive:
            ct_info = []
            for ct in to_remove:
                ct_info.append('    - Content type for %s.%s' % (ct.app_label, ct.model))
                collector = NoFastDeleteCollector(using=using)
                collector.collect([ct])

                for obj_type, objs in collector.data.items():
                    if objs == {ct}:
                        continue
                    ct_info.append('    - %s object%s of type %s.%s:' % (
                        len(objs),
                        's' if len(objs) != 1 else '',
                        obj_type._meta.app_label,
                        obj_type._meta.model_name)
                    )

            content_type_display = '\n'.join(ct_info)
            print("""Some content types in your database are stale and can be deleted.
Any objects that depend on these content types will then also be deleted.
The content types, and the dependent objects that would be deleted, are:

%s

This list does not include data that might be in your database
outside of Django's models.

Are you sure you want to delete these content types?
If you're unsure, answer 'no'.
    """ % content_type_display)
            ok_to_delete = input("Type 'yes' to continue, or 'no' to cancel: ")
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


class NoFastDeleteCollector(Collector):
    def can_fast_delete(self, *args, **kwargs):
        """
        We always want to load the objects into memory so that we can display
        them to the user when asking confirmation.
        """
        return False
