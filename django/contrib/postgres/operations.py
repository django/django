from django.contrib.postgres.signals import (
    get_citext_oids,
    get_hstore_oids,
    register_type_handlers,
)
from django.db import NotSupportedError, router
from django.db.migrations import AddConstraint, AddIndex, RemoveIndex
from django.db.migrations.operations.base import Operation, OperationCategory
from django.db.models.constraints import CheckConstraint


class CreateExtension(Operation):
    reversible = True
    category = OperationCategory.ADDITION

    def __init__(self, name):
        self.name = name

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql" or not router.allow_migrate(
            schema_editor.connection.alias, app_label
        ):
            return
        if not self.extension_exists(schema_editor, self.name):
            schema_editor.execute(
                "CREATE EXTENSION IF NOT EXISTS %s"
                % schema_editor.quote_name(self.name)
            )
        # Clear cached, stale oids.
        get_hstore_oids.cache_clear()
        get_citext_oids.cache_clear()
        # Registering new type handlers cannot be done before the extension is
        # installed, otherwise a subsequent data migration would use the same
        # connection.
        register_type_handlers(schema_editor.connection)
        if hasattr(schema_editor.connection, "register_geometry_adapters"):
            schema_editor.connection.register_geometry_adapters(
                schema_editor.connection.connection, True
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if not router.allow_migrate(schema_editor.connection.alias, app_label):
            return
        if self.extension_exists(schema_editor, self.name):
            schema_editor.execute(
                "DROP EXTENSION IF EXISTS %s" % schema_editor.quote_name(self.name)
            )
        # Clear cached, stale oids.
        get_hstore_oids.cache_clear()
        get_citext_oids.cache_clear()

    def extension_exists(self, schema_editor, extension):
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_extension WHERE extname = %s",
                [extension],
            )
            return bool(cursor.fetchone())

    def describe(self):
        return "Creates extension %s" % self.name

    @property
    def migration_name_fragment(self):
        return "create_extension_%s" % self.name


class BloomExtension(CreateExtension):
    def __init__(self):
        self.name = "bloom"


class BtreeGinExtension(CreateExtension):
    def __init__(self):
        self.name = "btree_gin"


class BtreeGistExtension(CreateExtension):
    def __init__(self):
        self.name = "btree_gist"


class CITextExtension(CreateExtension):
    def __init__(self):
        self.name = "citext"


class CryptoExtension(CreateExtension):
    def __init__(self):
        self.name = "pgcrypto"


class HStoreExtension(CreateExtension):
    def __init__(self):
        self.name = "hstore"


class TrigramExtension(CreateExtension):
    def __init__(self):
        self.name = "pg_trgm"


class UnaccentExtension(CreateExtension):
    def __init__(self):
        self.name = "unaccent"


class NotInTransactionMixin:
    def _ensure_not_in_transaction(self, schema_editor):
        if schema_editor.connection.in_atomic_block:
            raise NotSupportedError(
                "The %s operation cannot be executed inside a transaction "
                "(set atomic = False on the migration)." % self.__class__.__name__
            )


class AddIndexConcurrently(NotInTransactionMixin, AddIndex):
    """Create an index using PostgreSQL's CREATE INDEX CONCURRENTLY syntax."""

    atomic = False
    category = OperationCategory.ADDITION

    def describe(self):
        return "Concurrently create index %s on field(s) %s of model %s" % (
            self.index.name,
            ", ".join(self.index.fields),
            self.model_name,
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        self._ensure_not_in_transaction(schema_editor)
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.add_index(model, self.index, concurrently=True)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self._ensure_not_in_transaction(schema_editor)
        model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.remove_index(model, self.index, concurrently=True)


class RemoveIndexConcurrently(NotInTransactionMixin, RemoveIndex):
    """Remove an index using PostgreSQL's DROP INDEX CONCURRENTLY syntax."""

    atomic = False
    category = OperationCategory.REMOVAL

    def describe(self):
        return "Concurrently remove index %s from %s" % (self.name, self.model_name)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        self._ensure_not_in_transaction(schema_editor)
        model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            from_model_state = from_state.models[app_label, self.model_name_lower]
            index = from_model_state.get_index_by_name(self.name)
            schema_editor.remove_index(model, index, concurrently=True)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self._ensure_not_in_transaction(schema_editor)
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            to_model_state = to_state.models[app_label, self.model_name_lower]
            index = to_model_state.get_index_by_name(self.name)
            schema_editor.add_index(model, index, concurrently=True)


class CollationOperation(Operation):
    def __init__(self, name, locale, *, provider="libc", deterministic=True):
        self.name = name
        self.locale = locale
        self.provider = provider
        self.deterministic = deterministic

    def state_forwards(self, app_label, state):
        pass

    def deconstruct(self):
        kwargs = {"name": self.name, "locale": self.locale}
        if self.provider and self.provider != "libc":
            kwargs["provider"] = self.provider
        if self.deterministic is False:
            kwargs["deterministic"] = self.deterministic
        return (
            self.__class__.__qualname__,
            [],
            kwargs,
        )

    def create_collation(self, schema_editor):
        args = {"locale": schema_editor.quote_name(self.locale)}
        if self.provider != "libc":
            args["provider"] = schema_editor.quote_name(self.provider)
        if self.deterministic is False:
            args["deterministic"] = "false"
        schema_editor.execute(
            "CREATE COLLATION %(name)s (%(args)s)"
            % {
                "name": schema_editor.quote_name(self.name),
                "args": ", ".join(
                    f"{option}={value}" for option, value in args.items()
                ),
            }
        )

    def remove_collation(self, schema_editor):
        schema_editor.execute(
            "DROP COLLATION %s" % schema_editor.quote_name(self.name),
        )


class CreateCollation(CollationOperation):
    """Create a collation."""

    category = OperationCategory.ADDITION

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql" or not router.allow_migrate(
            schema_editor.connection.alias, app_label
        ):
            return
        self.create_collation(schema_editor)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if not router.allow_migrate(schema_editor.connection.alias, app_label):
            return
        self.remove_collation(schema_editor)

    def describe(self):
        return f"Create collation {self.name}"

    @property
    def migration_name_fragment(self):
        return "create_collation_%s" % self.name.lower()

    def reduce(self, operation, app_label):
        if isinstance(operation, RemoveCollation) and self.name == operation.name:
            return []
        return super().reduce(operation, app_label)


class RemoveCollation(CollationOperation):
    """Remove a collation."""

    category = OperationCategory.REMOVAL

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql" or not router.allow_migrate(
            schema_editor.connection.alias, app_label
        ):
            return
        self.remove_collation(schema_editor)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if not router.allow_migrate(schema_editor.connection.alias, app_label):
            return
        self.create_collation(schema_editor)

    def describe(self):
        return f"Remove collation {self.name}"

    @property
    def migration_name_fragment(self):
        return "remove_collation_%s" % self.name.lower()


class AddConstraintNotValid(AddConstraint):
    """
    Add a table constraint without enforcing validation, using PostgreSQL's
    NOT VALID syntax.
    """

    category = OperationCategory.ADDITION

    def __init__(self, model_name, constraint):
        if not isinstance(constraint, CheckConstraint):
            raise TypeError(
                "AddConstraintNotValid.constraint must be a check constraint."
            )
        super().__init__(model_name, constraint)

    def describe(self):
        return "Create not valid constraint %s on model %s" % (
            self.constraint.name,
            self.model_name,
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            constraint_sql = self.constraint.create_sql(model, schema_editor)
            if constraint_sql:
                # Constraint.create_sql returns interpolated SQL which makes
                # params=None a necessity to avoid escaping attempts on
                # execution.
                schema_editor.execute(str(constraint_sql) + " NOT VALID", params=None)

    @property
    def migration_name_fragment(self):
        return super().migration_name_fragment + "_not_valid"


class ValidateConstraint(Operation):
    """Validate a table NOT VALID constraint."""

    category = OperationCategory.ALTERATION

    def __init__(self, model_name, name):
        self.model_name = model_name
        self.name = name

    def describe(self):
        return "Validate constraint %s on model %s" % (self.name, self.model_name)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.execute(
                "ALTER TABLE %s VALIDATE CONSTRAINT %s"
                % (
                    schema_editor.quote_name(model._meta.db_table),
                    schema_editor.quote_name(self.name),
                )
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        # PostgreSQL does not provide a way to make a constraint invalid.
        pass

    def state_forwards(self, app_label, state):
        pass

    @property
    def migration_name_fragment(self):
        return "%s_validate_%s" % (self.model_name.lower(), self.name.lower())

    def deconstruct(self):
        return (
            self.__class__.__name__,
            [],
            {
                "model_name": self.model_name,
                "name": self.name,
            },
        )
