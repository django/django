from django.apps import apps as global_apps
from django.db import (
    DEFAULT_DB_ALIAS, IntegrityError, migrations, router, transaction,
)


class RenameContentType(migrations.RunPython):
    def __init__(self, app_label, old_model, new_model):
        self.app_label = app_label
        self.old_model = old_model
        self.new_model = new_model
        super().__init__(self.rename_forward, self.rename_backward)

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
                    content_type.save(using=db, update_fields={'model'})
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


def inject_rename_contenttypes(migration, operation, from_state, **kwargs):
    # Determine whether or not the ContentType model is available.
    if ('contenttypes', 'contenttype') not in from_state.models:
        return

    return [
        RenameContentType(
            migration.app_label,
            operation.old_name_lower,
            operation.new_name_lower,
        )
    ]


def get_contenttypes_and_models(app_config, using, ContentType):
    if not router.allow_migrate_model(using, ContentType):
        return None, None

    ContentType.objects.clear_cache()

    content_types = {
        ct.model: ct
        for ct in ContentType.objects.using(using).filter(app_label=app_config.label)
    }
    app_models = {
        model._meta.model_name: model
        for model in app_config.get_models()
    }
    return content_types, app_models


class CreateOrDeleteContentType(migrations.RunPython):
    def __init__(self, app_label, model, forward, backward):
        self.app_label = app_label
        self.model = model
        super().__init__(forward, backward)

    def delete(self, apps, schema_editor):
        ContentType = apps.get_model('contenttypes', 'ContentType')
        db = schema_editor.connection.alias
        if not router.allow_migrate_model(db, ContentType):
            return

        ContentType.objects.using(db).filter(
            app_label=self.app_label,
            model=self.model,
        ).delete()

    def create(self, apps, schema_editor):
        ContentType = apps.get_model('contenttypes', 'ContentType')
        db = schema_editor.connection.alias
        if not router.allow_migrate_model(db, ContentType):
            return

        ContentType.objects.using(db).get_or_create(
            app_label=self.app_label,
            model=self.model,
        )


class CreateContentType(CreateOrDeleteContentType):
    def __init__(self, app_label, model):
        super().__init__(app_label, model, self.create, self.delete)


class DeleteContentType(CreateOrDeleteContentType):
    def __init__(self, app_label, model):
        super().__init__(app_label, model, self.delete, self.create)


def inject_create_contenttypes(migration, operation, from_state, **kwargs):
    # Determine whether or not the ContentType model is available.
    if ('contenttypes', 'contenttype') not in from_state.models:
        return

    return [
        CreateContentType(migration.app_label, operation.name_lower),
    ]


def inject_delete_contenttypes(migration, operation, from_state, **kwargs):
    # Determine whether or not the ContentType model is available.
    if ('contenttypes', 'contenttype') not in from_state.models:
        return

    return [
        DeleteContentType(
            migration.app_label,
            operation.old_name_lower,
            operation.new_name_lower,
        )
    ]


def create_contenttypes(app_config, verbosity=2, interactive=True, using=DEFAULT_DB_ALIAS, apps=global_apps, **kwargs):
    """
    Create content types for models in the given app.
    """
    if not app_config.models_module:
        return

    app_label = app_config.label
    try:
        app_config = apps.get_app_config(app_label)
        ContentType = apps.get_model('contenttypes', 'ContentType')
    except LookupError:
        return

    content_types, app_models = get_contenttypes_and_models(app_config, using, ContentType)

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
