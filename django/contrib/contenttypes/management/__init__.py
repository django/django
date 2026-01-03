from django.apps import apps as global_apps
import warnings

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
            return

        # If a content type with the target model name already exists, try
        # to skip the rename to avoid a UNIQUE constraint failure. Be
        # defensive: tests may provide dummy managers/instances that don't
        # implement `filter()`/`pk`, so fall back to attempting the save if
        # we cannot perform this check.
        conflict_exists = False
        try:
            manager = ContentType.objects.db_manager(db)
            if hasattr(manager, "filter"):
                qs = manager.filter(app_label=self.app_label, model=new_model)
                if hasattr(content_type, "pk"):
                    qs = qs.exclude(pk=content_type.pk)
                conflict_exists = qs.exists()
        except Exception:
            conflict_exists = False

        if conflict_exists:
            warnings.warn(
                (
                    f"Could not rename ContentType '{old_model}' to "
                    f"'{new_model}' because a conflicting ContentType "
                    "already exists. The original name has been kept. "
                    "You may need to run 'remove_stale_contenttypes' to "
                    "resolve the conflict."
                ),
                RuntimeWarning,
            )
            return

        # Attempt to rename and persist only the model field.
        content_type.model = new_model
        try:
            with transaction.atomic(using=db):
                content_type.save(using=db, update_fields=["model"])
        except IntegrityError:
            # Revert and warn; ensure the outer migration transaction is
            # not left marked for rollback.
            content_type.model = old_model
            warnings.warn(
                (
                    f"Could not rename ContentType '{old_model}' to "
                    f"'{new_model}' due to an existing conflicting "
                    "content type. The original name has been kept. "
                    "You may need to run 'remove_stale_contenttypes' to "
                    "resolve the conflict."
                ),
                RuntimeWarning,
            )
            try:
                transaction.set_rollback(False, using=db)
            except Exception:
                pass
            return

        # Clear the cache as the `get_by_natural_key()` call will cache
        # the renamed ContentType instance by its old model name.
        if hasattr(ContentType.objects, "clear_cache"):
            ContentType.objects.clear_cache()

    def rename_forward(self, apps, schema_editor):
        self._rename(apps, schema_editor, self.old_model, self.new_model)

    def rename_backward(self, apps, schema_editor):
        self._rename(apps, schema_editor, self.new_model, self.old_model)


def inject_rename_contenttypes_operations(
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
        for inserted, (index, operation) in enumerate(inserts):
            migration.operations.insert(inserted + index, operation)


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

    try:
        app_config = apps.get_app_config(app_config.label)
        ContentType = apps.get_model("contenttypes", "ContentType")
    except LookupError:
        return

    if not router.allow_migrate_model(using, ContentType):
        return

    all_model_names = {model._meta.model_name for model in app_config.get_models()}

    if not all_model_names:
        return

    ContentType.objects.clear_cache()

    existing_model_names = set(
        ContentType.objects.using(using)
        .filter(app_label=app_config.label)
        .values_list("model", flat=True)
    )

    cts = [
        ContentType(app_label=app_config.label, model=model_name)
        for model_name in sorted(all_model_names - existing_model_names)
    ]
    ContentType.objects.using(using).bulk_create(cts)
    if verbosity >= 2:
        for ct in cts:
            print(f"Adding content type '{ct.app_label} | {ct.model}'")
