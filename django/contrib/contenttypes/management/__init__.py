from django.apps import apps as global_apps
from django.db import DEFAULT_DB_ALIAS, IntegrityError, migrations, router, transaction


class RenameContentType(migrations.RunPython):
    def __init__(self, app_label, old_model, new_model):
        self.app_label = app_label
        self.old_model = old_model
        self.new_model = new_model
        super().__init__(self.rename_forward, self.rename_backward)

    def _rename(self, apps, schema_editor, old_model, new_model):
        ContentType = apps.get_model("contenttypes", "ContentType")
        db = schema_editor.connection.alias
        if not router.allow_migrate_model(db, ContentType):
            return

        try:
            content_type = ContentType.objects.db_manager(db).get_by_natural_key(
                self.app_label, old_model
            )
        except ContentType.DoesNotExist:
            pass
        else:
            content_type.model = new_model
            try:
                with transaction.atomic(using=db):
                    content_type.save(using=db, update_fields={"model"})
            except IntegrityError:
                # Gracefully fallback if a stale content type causes a
                # conflict as remove_stale_contenttypes will take care of
                # asking the user what should be done next.
                content_type.model = old_model
            else:
                # Clear the cache as the `get_by_natural_key()` call will cache
                # the renamed ContentType instance by its old model name.
                ContentType.objects.clear_cache()

    def rename_forward(self, apps, schema_editor):
        self._rename(apps, schema_editor, self.old_model, self.new_model)

    def rename_backward(self, apps, schema_editor):
        self._rename(apps, schema_editor, self.new_model, self.old_model)


class MoveContentType(migrations.RunPython):
    def __init__(self, new_app_label, old_app_label, model_name):
        self.new_app_label = new_app_label
        self.old_app_label = old_app_label
        self.model_name = model_name
        super().__init__(self.move_model_forward, self.move_model_backward)

    def _move_model(self, apps, schema_editor, old_app_label, new_app_label):
        ContentType = apps.get_model("contenttypes", "ContentType")
        db = schema_editor.connection.alias
        if not router.allow_migrate_model(db, ContentType):
            return
        try:
            content_type = ContentType.objects.db_manager(db).get_by_natural_key(
                old_app_label, self.model_name
            )
        except ContentType.DoesNotExist:
            pass
        else:
            content_type.app_label = new_app_label
            try:
                with transaction.atomic(using=db):
                    content_type.save(using=db, update_fields={"app_label"})
            except IntegrityError:
                content_type.app_label = new_app_label
            else:
                ContentType.objects.clear_cache()

    def move_model_forward(self, apps, schema_editor):
        self._move_model(apps, schema_editor, self.old_app_label, self.new_app_label)

    def move_model_backward(self, apps, schema_editor):
        self._move_model(apps, schema_editor, self.new_app_label, self.old_app_label)


def inject_modify_contenttypes_operations(
    plan=None, apps=global_apps, using=DEFAULT_DB_ALIAS, **kwargs
):
    """
    Insert a `RenameContentType` operation after every planned `RenameModel`
    operation.
    """
    if plan is None:
        return

    # Determine whether or not the ContentType model is available.
    try:
        ContentType = apps.get_model("contenttypes", "ContentType")
    except LookupError:
        available = False
    else:
        if not router.allow_migrate_model(using, ContentType):
            return
        available = True

    for migration, backward in plan:
        if (migration.app_label, migration.name) == ("contenttypes", "0001_initial"):
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
                    migration.app_label,
                    operation.old_name_lower,
                    operation.new_name_lower,
                )
                inserts.append((index + 1, operation))
            if isinstance(
                operation, migrations.CreateModel
            ) and not operation.options.get(
                "old_app_label", None
            ) == operation.options.get(
                "app_label", None
            ):
                operation = MoveContentType(
                    migration.app_label,
                    operation.options["old_app_label"],
                    operation.name_lower,
                )
                inserts.append((index + 1, operation))
        for inserted, (index, operation) in enumerate(inserts):
            migration.operations.insert(inserted + index, operation)


def get_contenttypes_and_models(app_config, using, ContentType):
    if not router.allow_migrate_model(using, ContentType):
        return None, None

    ContentType.objects.clear_cache()

    content_types = {
        ct.model: ct
        for ct in ContentType.objects.using(using).filter(app_label=app_config.label)
    }
    app_models = {model._meta.model_name: model for model in app_config.get_models()}
    return content_types, app_models


def create_contenttypes(
    app_config,
    verbosity=2,
    interactive=True,
    using=DEFAULT_DB_ALIAS,
    apps=global_apps,
    **kwargs,
):
    """
    Create content types for models in the given app.
    """
    if not app_config.models_module:
        return

    app_label = app_config.label
    try:
        app_config = apps.get_app_config(app_label)
        ContentType = apps.get_model("contenttypes", "ContentType")
    except LookupError:
        return

    content_types, app_models = get_contenttypes_and_models(
        app_config, using, ContentType
    )

    if not app_models:
        return

    cts = [
        ContentType(
            app_label=app_label,
            model=model_name,
        )
        for (model_name, model) in app_models.items()
        if model_name not in content_types
    ]
    ContentType.objects.using(using).bulk_create(cts)
    if verbosity >= 2:
        for ct in cts:
            print("Adding content type '%s | %s'" % (ct.app_label, ct.model))
