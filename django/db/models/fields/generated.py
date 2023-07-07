from django.core import checks
from django.db import connections
from django.db.models.sql import Query

from . import Field

__all__ = ["GeneratedField"]


class GeneratedField(Field):
    generated = True
    db_returning = True

    _query = None
    _resolved_expression = None
    output_field = None

    def __init__(self, *, expression, output_field=None, db_persist=True, **kwargs):
        self.expression = expression
        self._output_field = output_field
        self.db_persist = db_persist

        assert "editable" not in kwargs, "Cannot set `editable` for GeneratedField"
        assert "blank" not in kwargs, "Cannot set `blank` for GeneratedField"
        assert "default" not in kwargs, "Cannot set `default` for GeneratedField"

        kwargs["editable"] = False
        kwargs["blank"] = True
        kwargs["default"] = None

        super().__init__(**kwargs)

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

    def _expression_sql(self, connection):
        return self._resolved_expression.as_sql(
            compiler=connection.ops.compiler("SQLCompiler")(
                self._query, connection=connection, using=None
            ),
            connection=connection,
        )

    def check(self, **kwargs):
        databases = kwargs.get("databases") or []
        return [
            *super().check(**kwargs),
            *self._check_sql_expression(databases),
            *self._check_persistence(databases),
        ]

    def _check_sql_expression(self, databases):
        errors = []
        for db in databases:
            connection = connections[db]

            if not (
                connection.features.supports_generated_columns
                or "supports_generated_columns" in self.model._meta.required_db_features
            ):
                errors.append(
                    checks.Error(
                        "%s does not support GeneratedFields."
                        % connection.display_name,
                        obj=self,
                        id="fields.E220",
                    )
                )

            if connection.features.supports_generated_columns:
                _, params = self._expression_sql(connection=connection)
                if params and not (
                    connection.features.supports_generated_columns_params
                    or "supports_generated_columns_params"
                    in self.model._meta.required_db_features
                ):
                    errors.append(
                        checks.Error(
                            "%s does not support GeneratedFields with "
                            "parameters." % connection.display_name,
                            obj=self,
                            id="fields.E221",
                        )
                    )

        return errors

    def _check_persistence(self, databases):
        errors = []

        for db in databases:
            connection = connections[db]

            if not self.db_persist and not (
                connection.features.supports_virtual_generated_columns
                or "supports_virtual_generated_columns"
                in self.model._meta.required_db_features
            ):
                errors.append(
                    checks.Error(
                        "%s does not support non-persisted GeneratedFields."
                        % connection.display_name,
                        obj=self,
                        id="fields.E222",
                        hint="remove the persisted=False argument",
                    )
                )

        return errors

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["blank"]
        del kwargs["default"]
        del kwargs["editable"]
        kwargs["expression"] = self.expression
        if self._output_field is not None:
            kwargs["output_field"] = self._output_field
        if self.db_persist is not True:
            kwargs["db_persist"] = self.db_persist
        return name, path, args, kwargs

    def db_parameters(self, connection):
        db_params = self.output_field.db_parameters(connection)
        expression_sql, params = self._expression_sql(connection=connection)
        db_params["generated_parameters"] = (expression_sql, self.db_persist, params)
        return db_params
