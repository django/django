from types import NoneType

from django.db.backends.utils import names_digest, split_identifier
from django.db.models.expressions import Col, ExpressionList, F, Func, OrderBy
from django.db.models.functions import Collate
from django.db.models.query_utils import Q
from django.db.models.sql import Query
from django.utils.functional import partition

__all__ = ["Index"]


class Index:
    suffix = "idx"
    # The max length of the name of the index (restricted to 30 for
    # cross-database compatibility with Oracle)
    max_name_length = 30

    def __init__(
        self,
        *expressions,
        fields=(),
        name=None,
        db_tablespace=None,
        opclasses=(),
        condition=None,
        include=None,
    ):
        if opclasses and not name:
            raise ValueError("An index must be named to use opclasses.")
        if not isinstance(condition, (NoneType, Q)):
            raise ValueError("Index.condition must be a Q instance.")
        if condition and not name:
            raise ValueError("An index must be named to use condition.")
        if not isinstance(fields, (list, tuple)):
            raise ValueError("Index.fields must be a list or tuple.")
        if not isinstance(opclasses, (list, tuple)):
            raise ValueError("Index.opclasses must be a list or tuple.")
        if not expressions and not fields:
            raise ValueError(
                "At least one field or expression is required to define an index."
            )
        if expressions and fields:
            raise ValueError(
                "Index.fields and expressions are mutually exclusive.",
            )
        if expressions and not name:
            raise ValueError("An index must be named to use expressions.")
        if expressions and opclasses:
            raise ValueError(
                "Index.opclasses cannot be used with expressions. Use "
                "django.contrib.postgres.indexes.OpClass() instead."
            )
        if opclasses and len(fields) != len(opclasses):
            raise ValueError(
                "Index.fields and Index.opclasses must have the same number of "
                "elements."
            )
        if fields and not all(isinstance(field, str) for field in fields):
            raise ValueError("Index.fields must contain only strings with field names.")
        if include and not name:
            raise ValueError("A covering index must be named.")
        if not isinstance(include, (NoneType, list, tuple)):
            raise ValueError("Index.include must be a list or tuple.")
        self.fields = list(fields)
        # A list of 2-tuple with the field name and ordering ('' or 'DESC').
        self.fields_orders = [
            (field_name.removeprefix("-"), "DESC" if field_name.startswith("-") else "")
            for field_name in self.fields
        ]
        self.name = name or ""
        self.db_tablespace = db_tablespace
        self.opclasses = opclasses
        self.condition = condition
        self.include = tuple(include) if include else ()
        self.expressions = tuple(
            F(expression) if isinstance(expression, str) else expression
            for expression in expressions
        )

    @property
    def contains_expressions(self):
        return bool(self.expressions)

    def _get_condition_sql(self, model, schema_editor):
        if self.condition is None:
            return None
        query = Query(model=model, alias_cols=False)
        where = query.build_where(self.condition)
        compiler = query.get_compiler(connection=schema_editor.connection)
        sql, params = where.as_sql(compiler, schema_editor.connection)
        return sql % tuple(schema_editor.quote_value(p) for p in params)

    def create_sql(self, model, schema_editor, using="", **kwargs):
        include = [
            model._meta.get_field(field_name).column for field_name in self.include
        ]
        condition = self._get_condition_sql(model, schema_editor)
        if self.expressions:
            index_expressions = []
            for expression in self.expressions:
                index_expression = IndexExpression(expression)
                index_expression.set_wrapper_classes(schema_editor.connection)
                index_expressions.append(index_expression)
            expressions = ExpressionList(*index_expressions).resolve_expression(
                Query(model, alias_cols=False),
            )
            fields = None
            col_suffixes = None
        else:
            fields = [
                model._meta.get_field(field_name)
                for field_name, _ in self.fields_orders
            ]
            if schema_editor.connection.features.supports_index_column_ordering:
                col_suffixes = [order[1] for order in self.fields_orders]
            else:
                col_suffixes = [""] * len(self.fields_orders)
            expressions = None
        return schema_editor._create_index_sql(
            model,
            fields=fields,
            name=self.name,
            using=using,
            db_tablespace=self.db_tablespace,
            col_suffixes=col_suffixes,
            opclasses=self.opclasses,
            condition=condition,
            include=include,
            expressions=expressions,
            **kwargs,
        )

    def remove_sql(self, model, schema_editor, **kwargs):
        return schema_editor._delete_index_sql(model, self.name, **kwargs)

    def deconstruct(self):
        path = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
        path = path.replace("django.db.models.indexes", "django.db.models")
        kwargs = {"name": self.name}
        if self.fields:
            kwargs["fields"] = self.fields
        if self.db_tablespace is not None:
            kwargs["db_tablespace"] = self.db_tablespace
        if self.opclasses:
            kwargs["opclasses"] = self.opclasses
        if self.condition:
            kwargs["condition"] = self.condition
        if self.include:
            kwargs["include"] = self.include
        return (path, self.expressions, kwargs)

    def clone(self):
        """Create a copy of this Index."""
        _, args, kwargs = self.deconstruct()
        return self.__class__(*args, **kwargs)

    def set_name_with_model(self, model):
        """
        Generate a unique name for the index.

        The name is divided into 3 parts - table name (12 chars), field name
        (8 chars) and unique hash + suffix (10 chars). Each part is made to
        fit its size by truncating the excess length.
        """
        _, table_name = split_identifier(model._meta.db_table)
        column_names = [
            model._meta.get_field(field_name).column
            for field_name, order in self.fields_orders
        ]
        column_names_with_order = [
            (("-%s" if order else "%s") % column_name)
            for column_name, (field_name, order) in zip(
                column_names, self.fields_orders
            )
        ]
        # The length of the parts of the name is based on the default max
        # length of 30 characters.
        hash_data = [table_name] + column_names_with_order + [self.suffix]
        self.name = "%s_%s_%s" % (
            table_name[:11],
            column_names[0][:7],
            "%s_%s" % (names_digest(*hash_data, length=6), self.suffix),
        )
        if len(self.name) > self.max_name_length:
            raise ValueError(
                "Index too long for multiple database support. Is self.suffix "
                "longer than 3 characters?"
            )
        if self.name[0] == "_" or self.name[0].isdigit():
            self.name = "D%s" % self.name[1:]

    def __repr__(self):
        return "<%s:%s%s%s%s%s%s%s>" % (
            self.__class__.__qualname__,
            "" if not self.fields else " fields=%s" % repr(self.fields),
            "" if not self.expressions else " expressions=%s" % repr(self.expressions),
            "" if not self.name else " name=%s" % repr(self.name),
            ""
            if self.db_tablespace is None
            else " db_tablespace=%s" % repr(self.db_tablespace),
            "" if self.condition is None else " condition=%s" % self.condition,
            "" if not self.include else " include=%s" % repr(self.include),
            "" if not self.opclasses else " opclasses=%s" % repr(self.opclasses),
        )

    def __eq__(self, other):
        if self.__class__ == other.__class__:
            return self.deconstruct() == other.deconstruct()
        return NotImplemented


class IndexExpression(Func):
    """Order and wrap expressions for CREATE INDEX statements."""

    template = "%(expressions)s"
    wrapper_classes = (OrderBy, Collate)

    def set_wrapper_classes(self, connection=None):
        # Some databases (e.g. MySQL) treats COLLATE as an indexed expression.
        if connection and connection.features.collate_as_index_expression:
            self.wrapper_classes = tuple(
                [
                    wrapper_cls
                    for wrapper_cls in self.wrapper_classes
                    if wrapper_cls is not Collate
                ]
            )

    @classmethod
    def register_wrappers(cls, *wrapper_classes):
        cls.wrapper_classes = wrapper_classes

    def resolve_expression(
        self,
        query=None,
        allow_joins=True,
        reuse=None,
        summarize=False,
        for_save=False,
    ):
        expressions = list(self.flatten())
        # Split expressions and wrappers.
        index_expressions, wrappers = partition(
            lambda e: isinstance(e, self.wrapper_classes),
            expressions,
        )
        wrapper_types = [type(wrapper) for wrapper in wrappers]
        if len(wrapper_types) != len(set(wrapper_types)):
            raise ValueError(
                "Multiple references to %s can't be used in an indexed "
                "expression."
                % ", ".join(
                    [wrapper_cls.__qualname__ for wrapper_cls in self.wrapper_classes]
                )
            )
        if expressions[1 : len(wrappers) + 1] != wrappers:
            raise ValueError(
                "%s must be topmost expressions in an indexed expression."
                % ", ".join(
                    [wrapper_cls.__qualname__ for wrapper_cls in self.wrapper_classes]
                )
            )
        # Wrap expressions in parentheses if they are not column references.
        root_expression = index_expressions[1]
        resolve_root_expression = root_expression.resolve_expression(
            query,
            allow_joins,
            reuse,
            summarize,
            for_save,
        )
        if not isinstance(resolve_root_expression, Col):
            root_expression = Func(root_expression, template="(%(expressions)s)")

        if wrappers:
            # Order wrappers and set their expressions.
            wrappers = sorted(
                wrappers,
                key=lambda w: self.wrapper_classes.index(type(w)),
            )
            wrappers = [wrapper.copy() for wrapper in wrappers]
            for i, wrapper in enumerate(wrappers[:-1]):
                wrapper.set_source_expressions([wrappers[i + 1]])
            # Set the root expression on the deepest wrapper.
            wrappers[-1].set_source_expressions([root_expression])
            self.set_source_expressions([wrappers[0]])
        else:
            # Use the root expression, if there are no wrappers.
            self.set_source_expressions([root_expression])
        return super().resolve_expression(
            query, allow_joins, reuse, summarize, for_save
        )

    def as_sqlite(self, compiler, connection, **extra_context):
        # Casting to numeric is unnecessary.
        return self.as_sql(compiler, connection, **extra_context)
