import warnings
from enum import Enum
from types import NoneType

from django.core import checks
from django.core.exceptions import FieldDoesNotExist, FieldError, ValidationError
from django.db import connections
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Exists, ExpressionList, F, RawSQL
from django.db.models.indexes import IndexExpression
from django.db.models.lookups import Exact, IsNull
from django.db.models.query_utils import Q
from django.db.models.sql.query import Query
from django.db.utils import DEFAULT_DB_ALIAS
from django.utils.deprecation import RemovedInDjango60Warning
from django.utils.translation import gettext_lazy as _

__all__ = ["BaseConstraint", "CheckConstraint", "Deferrable", "UniqueConstraint"]


class BaseConstraint:
    default_violation_error_message = _("Constraint “%(name)s” is violated.")
    violation_error_code = None
    violation_error_message = None

    # RemovedInDjango60Warning: When the deprecation ends, replace with:
    # def __init__(
    #     self, *, name, violation_error_code=None, violation_error_message=None
    # ):
    def __init__(
        self, *args, name=None, violation_error_code=None, violation_error_message=None
    ):
        # RemovedInDjango60Warning.
        if name is None and not args:
            raise TypeError(
                f"{self.__class__.__name__}.__init__() missing 1 required keyword-only "
                f"argument: 'name'"
            )
        self.name = name
        if violation_error_code is not None:
            self.violation_error_code = violation_error_code
        if violation_error_message is not None:
            self.violation_error_message = violation_error_message
        else:
            self.violation_error_message = self.default_violation_error_message
        # RemovedInDjango60Warning.
        if args:
            warnings.warn(
                f"Passing positional arguments to {self.__class__.__name__} is "
                f"deprecated.",
                RemovedInDjango60Warning,
                stacklevel=2,
            )
            for arg, attr in zip(args, ["name", "violation_error_message"]):
                if arg:
                    setattr(self, attr, arg)

    @property
    def contains_expressions(self):
        return False

    def constraint_sql(self, model, schema_editor):
        raise NotImplementedError("This method must be implemented by a subclass.")

    def create_sql(self, model, schema_editor):
        raise NotImplementedError("This method must be implemented by a subclass.")

    def remove_sql(self, model, schema_editor):
        raise NotImplementedError("This method must be implemented by a subclass.")

    def validate(self, model, instance, exclude=None, using=DEFAULT_DB_ALIAS):
        raise NotImplementedError("This method must be implemented by a subclass.")

    def get_violation_error_message(self):
        return self.violation_error_message % {"name": self.name}

    def _check(self, model, connection):
        return []

    def _check_references(self, model, references):
        errors = []
        fields = set()
        for field_name, *lookups in references:
            # pk is an alias that won't be found by opts.get_field.
            if field_name != "pk":
                fields.add(field_name)
            if not lookups:
                # If it has no lookups it cannot result in a JOIN.
                continue
            try:
                if field_name == "pk":
                    field = model._meta.pk
                else:
                    field = model._meta.get_field(field_name)
                if not field.is_relation or field.many_to_many or field.one_to_many:
                    continue
            except FieldDoesNotExist:
                continue
            # JOIN must happen at the first lookup.
            first_lookup = lookups[0]
            if (
                hasattr(field, "get_transform")
                and hasattr(field, "get_lookup")
                and field.get_transform(first_lookup) is None
                and field.get_lookup(first_lookup) is None
            ):
                errors.append(
                    checks.Error(
                        "'constraints' refers to the joined field '%s'."
                        % LOOKUP_SEP.join([field_name] + lookups),
                        obj=model,
                        id="models.E041",
                    )
                )
        errors.extend(model._check_local_fields(fields, "constraints"))
        return errors

    def deconstruct(self):
        path = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
        path = path.replace("django.db.models.constraints", "django.db.models")
        kwargs = {"name": self.name}
        if (
            self.violation_error_message is not None
            and self.violation_error_message != self.default_violation_error_message
        ):
            kwargs["violation_error_message"] = self.violation_error_message
        if self.violation_error_code is not None:
            kwargs["violation_error_code"] = self.violation_error_code
        return (path, (), kwargs)

    def clone(self):
        _, args, kwargs = self.deconstruct()
        return self.__class__(*args, **kwargs)


class CheckConstraint(BaseConstraint):
    # RemovedInDjango60Warning: when the deprecation ends, replace with
    # def __init__(
    #  self, *, condition, name, violation_error_code=None, violation_error_message=None
    # )
    def __init__(
        self,
        *,
        name,
        condition=None,
        check=None,
        violation_error_code=None,
        violation_error_message=None,
    ):
        if check is not None:
            warnings.warn(
                "CheckConstraint.check is deprecated in favor of `.condition`.",
                RemovedInDjango60Warning,
                stacklevel=2,
            )
            condition = check
        self.condition = condition
        if not getattr(condition, "conditional", False):
            raise TypeError(
                "CheckConstraint.condition must be a Q instance or boolean expression."
            )
        super().__init__(
            name=name,
            violation_error_code=violation_error_code,
            violation_error_message=violation_error_message,
        )

    def _get_check(self):
        warnings.warn(
            "CheckConstraint.check is deprecated in favor of `.condition`.",
            RemovedInDjango60Warning,
            stacklevel=2,
        )
        return self.condition

    def _set_check(self, value):
        warnings.warn(
            "CheckConstraint.check is deprecated in favor of `.condition`.",
            RemovedInDjango60Warning,
            stacklevel=2,
        )
        self.condition = value

    check = property(_get_check, _set_check)

    def _check(self, model, connection):
        errors = []
        if not (
            connection.features.supports_table_check_constraints
            or "supports_table_check_constraints" in model._meta.required_db_features
        ):
            errors.append(
                checks.Warning(
                    f"{connection.display_name} does not support check constraints.",
                    hint=(
                        "A constraint won't be created. Silence this warning if you "
                        "don't care about it."
                    ),
                    obj=model,
                    id="models.W027",
                )
            )
        elif (
            connection.features.supports_table_check_constraints
            or "supports_table_check_constraints"
            not in model._meta.required_db_features
        ):
            references = set()
            condition = self.condition
            if isinstance(condition, Q):
                references.update(model._get_expr_references(condition))
            if any(isinstance(expr, RawSQL) for expr in condition.flatten()):
                errors.append(
                    checks.Warning(
                        f"Check constraint {self.name!r} contains RawSQL() expression "
                        "and won't be validated during the model full_clean().",
                        hint="Silence this warning if you don't care about it.",
                        obj=model,
                        id="models.W045",
                    ),
                )
            errors.extend(self._check_references(model, references))
        return errors

    def _get_check_sql(self, model, schema_editor):
        query = Query(model=model, alias_cols=False)
        where = query.build_where(self.condition)
        compiler = query.get_compiler(connection=schema_editor.connection)
        sql, params = where.as_sql(compiler, schema_editor.connection)
        return sql % tuple(schema_editor.quote_value(p) for p in params)

    def constraint_sql(self, model, schema_editor):
        check = self._get_check_sql(model, schema_editor)
        return schema_editor._check_sql(self.name, check)

    def create_sql(self, model, schema_editor):
        check = self._get_check_sql(model, schema_editor)
        return schema_editor._create_check_sql(model, self.name, check)

    def remove_sql(self, model, schema_editor):
        return schema_editor._delete_check_sql(model, self.name)

    def validate(self, model, instance, exclude=None, using=DEFAULT_DB_ALIAS):
        against = instance._get_field_value_map(meta=model._meta, exclude=exclude)
        try:
            if not Q(self.condition).check(against, using=using):
                raise ValidationError(
                    self.get_violation_error_message(), code=self.violation_error_code
                )
        except FieldError:
            pass

    def __repr__(self):
        return "<%s: condition=%s name=%s%s%s>" % (
            self.__class__.__qualname__,
            self.condition,
            repr(self.name),
            (
                ""
                if self.violation_error_code is None
                else " violation_error_code=%r" % self.violation_error_code
            ),
            (
                ""
                if self.violation_error_message is None
                or self.violation_error_message == self.default_violation_error_message
                else " violation_error_message=%r" % self.violation_error_message
            ),
        )

    def __eq__(self, other):
        if isinstance(other, CheckConstraint):
            return (
                self.name == other.name
                and self.condition == other.condition
                and self.violation_error_code == other.violation_error_code
                and self.violation_error_message == other.violation_error_message
            )
        return super().__eq__(other)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs["condition"] = self.condition
        return path, args, kwargs


class Deferrable(Enum):
    DEFERRED = "deferred"
    IMMEDIATE = "immediate"

    # A similar format was proposed for Python 3.10.
    def __repr__(self):
        return f"{self.__class__.__qualname__}.{self._name_}"


class UniqueConstraint(BaseConstraint):
    def __init__(
        self,
        *expressions,
        fields=(),
        name=None,
        condition=None,
        deferrable=None,
        include=None,
        opclasses=(),
        nulls_distinct=None,
        violation_error_code=None,
        violation_error_message=None,
    ):
        if not name:
            raise ValueError("A unique constraint must be named.")
        if not expressions and not fields:
            raise ValueError(
                "At least one field or expression is required to define a "
                "unique constraint."
            )
        if expressions and fields:
            raise ValueError(
                "UniqueConstraint.fields and expressions are mutually exclusive."
            )
        if not isinstance(condition, (NoneType, Q)):
            raise ValueError("UniqueConstraint.condition must be a Q instance.")
        if condition and deferrable:
            raise ValueError("UniqueConstraint with conditions cannot be deferred.")
        if include and deferrable:
            raise ValueError("UniqueConstraint with include fields cannot be deferred.")
        if opclasses and deferrable:
            raise ValueError("UniqueConstraint with opclasses cannot be deferred.")
        if expressions and deferrable:
            raise ValueError("UniqueConstraint with expressions cannot be deferred.")
        if expressions and opclasses:
            raise ValueError(
                "UniqueConstraint.opclasses cannot be used with expressions. "
                "Use django.contrib.postgres.indexes.OpClass() instead."
            )
        if not isinstance(deferrable, (NoneType, Deferrable)):
            raise TypeError(
                "UniqueConstraint.deferrable must be a Deferrable instance."
            )
        if not isinstance(include, (NoneType, list, tuple)):
            raise TypeError("UniqueConstraint.include must be a list or tuple.")
        if not isinstance(opclasses, (list, tuple)):
            raise TypeError("UniqueConstraint.opclasses must be a list or tuple.")
        if not isinstance(nulls_distinct, (NoneType, bool)):
            raise TypeError("UniqueConstraint.nulls_distinct must be a bool.")
        if opclasses and len(fields) != len(opclasses):
            raise ValueError(
                "UniqueConstraint.fields and UniqueConstraint.opclasses must "
                "have the same number of elements."
            )
        self.fields = tuple(fields)
        self.condition = condition
        self.deferrable = deferrable
        self.include = tuple(include) if include else ()
        self.opclasses = opclasses
        self.nulls_distinct = nulls_distinct
        self.expressions = tuple(
            F(expression) if isinstance(expression, str) else expression
            for expression in expressions
        )
        super().__init__(
            name=name,
            violation_error_code=violation_error_code,
            violation_error_message=violation_error_message,
        )

    @property
    def contains_expressions(self):
        return bool(self.expressions)

    def _check(self, model, connection):
        errors = model._check_local_fields({*self.fields, *self.include}, "constraints")
        required_db_features = model._meta.required_db_features
        if self.condition is not None and not (
            connection.features.supports_partial_indexes
            or "supports_partial_indexes" in required_db_features
        ):
            errors.append(
                checks.Warning(
                    f"{connection.display_name} does not support unique constraints "
                    "with conditions.",
                    hint=(
                        "A constraint won't be created. Silence this warning if you "
                        "don't care about it."
                    ),
                    obj=model,
                    id="models.W036",
                )
            )
        if self.deferrable is not None and not (
            connection.features.supports_deferrable_unique_constraints
            or "supports_deferrable_unique_constraints" in required_db_features
        ):
            errors.append(
                checks.Warning(
                    f"{connection.display_name} does not support deferrable unique "
                    "constraints.",
                    hint=(
                        "A constraint won't be created. Silence this warning if you "
                        "don't care about it."
                    ),
                    obj=model,
                    id="models.W038",
                )
            )
        if self.include and not (
            connection.features.supports_covering_indexes
            or "supports_covering_indexes" in required_db_features
        ):
            errors.append(
                checks.Warning(
                    f"{connection.display_name} does not support unique constraints "
                    "with non-key columns.",
                    hint=(
                        "A constraint won't be created. Silence this warning if you "
                        "don't care about it."
                    ),
                    obj=model,
                    id="models.W039",
                )
            )
        if self.contains_expressions and not (
            connection.features.supports_expression_indexes
            or "supports_expression_indexes" in required_db_features
        ):
            errors.append(
                checks.Warning(
                    f"{connection.display_name} does not support unique constraints on "
                    "expressions.",
                    hint=(
                        "A constraint won't be created. Silence this warning if you "
                        "don't care about it."
                    ),
                    obj=model,
                    id="models.W044",
                )
            )
        if self.nulls_distinct is not None and not (
            connection.features.supports_nulls_distinct_unique_constraints
            or "supports_nulls_distinct_unique_constraints" in required_db_features
        ):
            errors.append(
                checks.Warning(
                    f"{connection.display_name} does not support unique constraints "
                    "with nulls distinct.",
                    hint=(
                        "A constraint won't be created. Silence this warning if you "
                        "don't care about it."
                    ),
                    obj=model,
                    id="models.W047",
                )
            )
        references = set()
        if (
            connection.features.supports_partial_indexes
            or "supports_partial_indexes" not in required_db_features
        ) and isinstance(self.condition, Q):
            references.update(model._get_expr_references(self.condition))
        if self.contains_expressions and (
            connection.features.supports_expression_indexes
            or "supports_expression_indexes" not in required_db_features
        ):
            for expression in self.expressions:
                references.update(model._get_expr_references(expression))
        errors.extend(self._check_references(model, references))
        return errors

    def _get_condition_sql(self, model, schema_editor):
        if self.condition is None:
            return None
        query = Query(model=model, alias_cols=False)
        where = query.build_where(self.condition)
        compiler = query.get_compiler(connection=schema_editor.connection)
        sql, params = where.as_sql(compiler, schema_editor.connection)
        return sql % tuple(schema_editor.quote_value(p) for p in params)

    def _get_index_expressions(self, model, schema_editor):
        if not self.expressions:
            return None
        index_expressions = []
        for expression in self.expressions:
            index_expression = IndexExpression(expression)
            index_expression.set_wrapper_classes(schema_editor.connection)
            index_expressions.append(index_expression)
        return ExpressionList(*index_expressions).resolve_expression(
            Query(model, alias_cols=False),
        )

    def constraint_sql(self, model, schema_editor):
        fields = [model._meta.get_field(field_name) for field_name in self.fields]
        include = [
            model._meta.get_field(field_name).column for field_name in self.include
        ]
        condition = self._get_condition_sql(model, schema_editor)
        expressions = self._get_index_expressions(model, schema_editor)
        return schema_editor._unique_sql(
            model,
            fields,
            self.name,
            condition=condition,
            deferrable=self.deferrable,
            include=include,
            opclasses=self.opclasses,
            expressions=expressions,
            nulls_distinct=self.nulls_distinct,
        )

    def create_sql(self, model, schema_editor):
        fields = [model._meta.get_field(field_name) for field_name in self.fields]
        include = [
            model._meta.get_field(field_name).column for field_name in self.include
        ]
        condition = self._get_condition_sql(model, schema_editor)
        expressions = self._get_index_expressions(model, schema_editor)
        return schema_editor._create_unique_sql(
            model,
            fields,
            self.name,
            condition=condition,
            deferrable=self.deferrable,
            include=include,
            opclasses=self.opclasses,
            expressions=expressions,
            nulls_distinct=self.nulls_distinct,
        )

    def remove_sql(self, model, schema_editor):
        condition = self._get_condition_sql(model, schema_editor)
        include = [
            model._meta.get_field(field_name).column for field_name in self.include
        ]
        expressions = self._get_index_expressions(model, schema_editor)
        return schema_editor._delete_unique_sql(
            model,
            self.name,
            condition=condition,
            deferrable=self.deferrable,
            include=include,
            opclasses=self.opclasses,
            expressions=expressions,
            nulls_distinct=self.nulls_distinct,
        )

    def __repr__(self):
        return "<%s:%s%s%s%s%s%s%s%s%s%s>" % (
            self.__class__.__qualname__,
            "" if not self.fields else " fields=%s" % repr(self.fields),
            "" if not self.expressions else " expressions=%s" % repr(self.expressions),
            " name=%s" % repr(self.name),
            "" if self.condition is None else " condition=%s" % self.condition,
            "" if self.deferrable is None else " deferrable=%r" % self.deferrable,
            "" if not self.include else " include=%s" % repr(self.include),
            "" if not self.opclasses else " opclasses=%s" % repr(self.opclasses),
            (
                ""
                if self.nulls_distinct is None
                else " nulls_distinct=%r" % self.nulls_distinct
            ),
            (
                ""
                if self.violation_error_code is None
                else " violation_error_code=%r" % self.violation_error_code
            ),
            (
                ""
                if self.violation_error_message is None
                or self.violation_error_message == self.default_violation_error_message
                else " violation_error_message=%r" % self.violation_error_message
            ),
        )

    def __eq__(self, other):
        if isinstance(other, UniqueConstraint):
            return (
                self.name == other.name
                and self.fields == other.fields
                and self.condition == other.condition
                and self.deferrable == other.deferrable
                and self.include == other.include
                and self.opclasses == other.opclasses
                and self.expressions == other.expressions
                and self.nulls_distinct is other.nulls_distinct
                and self.violation_error_code == other.violation_error_code
                and self.violation_error_message == other.violation_error_message
            )
        return super().__eq__(other)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.fields:
            kwargs["fields"] = self.fields
        if self.condition:
            kwargs["condition"] = self.condition
        if self.deferrable:
            kwargs["deferrable"] = self.deferrable
        if self.include:
            kwargs["include"] = self.include
        if self.opclasses:
            kwargs["opclasses"] = self.opclasses
        if self.nulls_distinct is not None:
            kwargs["nulls_distinct"] = self.nulls_distinct
        return path, self.expressions, kwargs

    def validate(self, model, instance, exclude=None, using=DEFAULT_DB_ALIAS):
        queryset = model._default_manager.using(using)
        if self.fields:
            lookup_kwargs = {}
            for field_name in self.fields:
                if exclude and field_name in exclude:
                    return
                field = model._meta.get_field(field_name)
                lookup_value = getattr(instance, field.attname)
                if (
                    self.nulls_distinct is not False
                    and lookup_value is None
                    or (
                        lookup_value == ""
                        and connections[
                            using
                        ].features.interprets_empty_strings_as_nulls
                    )
                ):
                    # A composite constraint containing NULL value cannot cause
                    # a violation since NULL != NULL in SQL.
                    return
                lookup_kwargs[field.name] = lookup_value
            queryset = queryset.filter(**lookup_kwargs)
        else:
            # Ignore constraints with excluded fields.
            if exclude:
                for expression in self.expressions:
                    if hasattr(expression, "flatten"):
                        for expr in expression.flatten():
                            if isinstance(expr, F) and expr.name in exclude:
                                return
                    elif isinstance(expression, F) and expression.name in exclude:
                        return
            replacements = {
                F(field): value
                for field, value in instance._get_field_value_map(
                    meta=model._meta, exclude=exclude
                ).items()
            }
            filters = []
            for expr in self.expressions:
                if hasattr(expr, "get_expression_for_validation"):
                    expr = expr.get_expression_for_validation()
                rhs = expr.replace_expressions(replacements)
                condition = Exact(expr, rhs)
                if self.nulls_distinct is False:
                    condition = Q(condition) | Q(IsNull(expr, True), IsNull(rhs, True))
                filters.append(condition)
            queryset = queryset.filter(*filters)
        model_class_pk = instance._get_pk_val(model._meta)
        if not instance._state.adding and model_class_pk is not None:
            queryset = queryset.exclude(pk=model_class_pk)
        if not self.condition:
            if queryset.exists():
                if self.fields:
                    # When fields are defined, use the unique_error_message() for
                    # backward compatibility.
                    raise ValidationError(
                        instance.unique_error_message(model, self.fields),
                    )
                raise ValidationError(
                    self.get_violation_error_message(),
                    code=self.violation_error_code,
                )
        else:
            against = instance._get_field_value_map(meta=model._meta, exclude=exclude)
            try:
                if (self.condition & Exists(queryset.filter(self.condition))).check(
                    against, using=using
                ):
                    raise ValidationError(
                        self.get_violation_error_message(),
                        code=self.violation_error_code,
                    )
            except FieldError:
                pass
