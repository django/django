from django.core import checks
from django.db import connections, router
from django.db.models.sql import Query
from django.utils.functional import cached_property

from . import NOT_PROVIDED, Field

__all__ = ["GeneratedField"]


class GeneratedField(Field):
    generated = True
    db_returning = True

    _query = None
    _resolved_expression = None
    output_field = None

    def __init__(self, *, expression, db_persist=None, output_field=None, **kwargs):
        if kwargs.setdefault("editable", False):
            raise ValueError("GeneratedField cannot be editable.")
        if not kwargs.setdefault("blank", True):
            raise ValueError("GeneratedField must be blank.")
        if kwargs.get("default", NOT_PROVIDED) is not NOT_PROVIDED:
            raise ValueError("GeneratedField cannot have a default.")
        if kwargs.get("db_default", NOT_PROVIDED) is not NOT_PROVIDED:
            raise ValueError("GeneratedField cannot have a database default.")
        if db_persist not in (True, False):
            raise ValueError("GeneratedField.db_persist must be True or False.")

        self.expression = expression
        self._output_field = output_field
        self.db_persist = db_persist
        super().__init__(**kwargs)

    @cached_property
    def cached_col(self):
        from django.db.models.expressions import Col

        return Col(self.model._meta.db_table, self, self.output_field)

    def get_col(self, alias, output_field=None):
        if alias != self.model._meta.db_table and output_field is None:
            output_field = self.output_field
        return super().get_col(alias, output_field)

    def contribute_to_class(self, *args, **kwargs):
        super().contribute_to_class(*args, **kwargs)

        self._query = Query(model=self.model, alias_cols=False)
        self._resolved_expression = self.expression.resolve_expression(
            self._query, allow_joins=False
        )
        self.output_field = (
            self._output_field
            if self._output_field is not None
            else self._resolved_expression.output_field
        )
        # Register lookups from the output_field class.
        for lookup_name, lookup in self.output_field.get_class_lookups().items():
            self.register_lookup(lookup, lookup_name=lookup_name)

    def generated_sql(self, connection):
        compiler = connection.ops.compiler("SQLCompiler")(
            self._query, connection=connection, using=None
        )
        return compiler.compile(self._resolved_expression)

    def check(self, **kwargs):
        databases = kwargs.get("databases") or []
        return [
            *super().check(**kwargs),
            *self._check_supported(databases),
            *self._check_persistence(databases),
        ]

    def _check_supported(self, databases):
        errors = []
        for db in databases:
            if not router.allow_migrate_model(db, self.model):
                continue
            connection = connections[db]
            if (
                self.model._meta.required_db_vendor
                and self.model._meta.required_db_vendor != connection.vendor
            ):
                continue
            if not (
                connection.features.supports_virtual_generated_columns
                or "supports_stored_generated_columns"
                in self.model._meta.required_db_features
            ) and not (
                connection.features.supports_stored_generated_columns
                or "supports_virtual_generated_columns"
                in self.model._meta.required_db_features
            ):
                errors.append(
                    checks.Error(
                        f"{connection.display_name} does not support GeneratedFields.",
                        obj=self,
                        id="fields.E220",
                    )
                )
        return errors

    def _check_persistence(self, databases):
        errors = []
        for db in databases:
            if not router.allow_migrate_model(db, self.model):
                continue
            connection = connections[db]
            if (
                self.model._meta.required_db_vendor
                and self.model._meta.required_db_vendor != connection.vendor
            ):
                continue
            if not self.db_persist and not (
                connection.features.supports_virtual_generated_columns
                or "supports_virtual_generated_columns"
                in self.model._meta.required_db_features
            ):
                errors.append(
                    checks.Error(
                        f"{connection.display_name} does not support non-persisted "
                        "GeneratedFields.",
                        obj=self,
                        id="fields.E221",
                        hint="Set db_persist=True on the field.",
                    )
                )
            if self.db_persist and not (
                connection.features.supports_stored_generated_columns
                or "supports_stored_generated_columns"
                in self.model._meta.required_db_features
            ):
                errors.append(
                    checks.Error(
                        f"{connection.display_name} does not support persisted "
                        "GeneratedFields.",
                        obj=self,
                        id="fields.E222",
                        hint="Set db_persist=False on the field.",
                    )
                )
        return errors

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["blank"]
        del kwargs["editable"]
        kwargs["db_persist"] = self.db_persist
        kwargs["expression"] = self.expression
        if self._output_field is not None:
            kwargs["output_field"] = self._output_field
        return name, path, args, kwargs

    def get_internal_type(self):
        return self.output_field.get_internal_type()

    def db_parameters(self, connection):
        return self.output_field.db_parameters(connection)
