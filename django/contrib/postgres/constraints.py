from django.db import NotSupportedError
from django.db.backends.ddl_references import Statement, Table
from django.db.models import Deferrable, F, Q
from django.db.models.constraints import BaseConstraint
from django.db.models.sql import Query

__all__ = ['ExclusionConstraint']


class ExclusionConstraint(BaseConstraint):
    template = 'CONSTRAINT %(name)s EXCLUDE USING %(index_type)s (%(expressions)s)%(include)s%(where)s%(deferrable)s'

    def __init__(
        self, *, name, expressions, index_type=None, condition=None,
        deferrable=None, include=None, opclasses=(),
    ):
        if index_type and index_type.lower() not in {'gist', 'spgist'}:
            raise ValueError(
                'Exclusion constraints only support GiST or SP-GiST indexes.'
            )
        if not expressions:
            raise ValueError(
                'At least one expression is required to define an exclusion '
                'constraint.'
            )
        if not all(
            isinstance(expr, (list, tuple)) and len(expr) == 2
            for expr in expressions
        ):
            raise ValueError('The expressions must be a list of 2-tuples.')
        if not isinstance(condition, (type(None), Q)):
            raise ValueError(
                'ExclusionConstraint.condition must be a Q instance.'
            )
        if condition and deferrable:
            raise ValueError(
                'ExclusionConstraint with conditions cannot be deferred.'
            )
        if not isinstance(deferrable, (type(None), Deferrable)):
            raise ValueError(
                'ExclusionConstraint.deferrable must be a Deferrable instance.'
            )
        if not isinstance(include, (type(None), list, tuple)):
            raise ValueError(
                'ExclusionConstraint.include must be a list or tuple.'
            )
        if include and index_type and index_type.lower() != 'gist':
            raise ValueError(
                'Covering exclusion constraints only support GiST indexes.'
            )
        if not isinstance(opclasses, (list, tuple)):
            raise ValueError(
                'ExclusionConstraint.opclasses must be a list or tuple.'
            )
        if opclasses and len(expressions) != len(opclasses):
            raise ValueError(
                'ExclusionConstraint.expressions and '
                'ExclusionConstraint.opclasses must have the same number of '
                'elements.'
            )
        self.expressions = expressions
        self.index_type = index_type or 'GIST'
        self.condition = condition
        self.deferrable = deferrable
        self.include = tuple(include) if include else ()
        self.opclasses = opclasses
        super().__init__(name=name)

    def _get_expression_sql(self, compiler, schema_editor, query):
        expressions = []
        for idx, (expression, operator) in enumerate(self.expressions):
            if isinstance(expression, str):
                expression = F(expression)
            expression = expression.resolve_expression(query=query)
            sql, params = compiler.compile(expression)
            try:
                opclass = self.opclasses[idx]
                if opclass:
                    sql = '%s %s' % (sql, opclass)
            except IndexError:
                pass
            sql = sql % tuple(schema_editor.quote_value(p) for p in params)
            expressions.append('%s WITH %s' % (sql, operator))
        return expressions

    def _get_condition_sql(self, compiler, schema_editor, query):
        if self.condition is None:
            return None
        where = query.build_where(self.condition)
        sql, params = where.as_sql(compiler, schema_editor.connection)
        return sql % tuple(schema_editor.quote_value(p) for p in params)

    def constraint_sql(self, model, schema_editor):
        query = Query(model, alias_cols=False)
        compiler = query.get_compiler(connection=schema_editor.connection)
        expressions = self._get_expression_sql(compiler, schema_editor, query)
        condition = self._get_condition_sql(compiler, schema_editor, query)
        include = [model._meta.get_field(field_name).column for field_name in self.include]
        return self.template % {
            'name': schema_editor.quote_name(self.name),
            'index_type': self.index_type,
            'expressions': ', '.join(expressions),
            'include': schema_editor._index_include_sql(model, include),
            'where': ' WHERE (%s)' % condition if condition else '',
            'deferrable': schema_editor._deferrable_constraint_sql(self.deferrable),
        }

    def create_sql(self, model, schema_editor):
        self.check_supported(schema_editor)
        return Statement(
            'ALTER TABLE %(table)s ADD %(constraint)s',
            table=Table(model._meta.db_table, schema_editor.quote_name),
            constraint=self.constraint_sql(model, schema_editor),
        )

    def remove_sql(self, model, schema_editor):
        return schema_editor._delete_constraint_sql(
            schema_editor.sql_delete_check,
            model,
            schema_editor.quote_name(self.name),
        )

    def check_supported(self, schema_editor):
        if self.include and not schema_editor.connection.features.supports_covering_gist_indexes:
            raise NotSupportedError(
                'Covering exclusion constraints requires PostgreSQL 12+.'
            )

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs['expressions'] = self.expressions
        if self.condition is not None:
            kwargs['condition'] = self.condition
        if self.index_type.lower() != 'gist':
            kwargs['index_type'] = self.index_type
        if self.deferrable:
            kwargs['deferrable'] = self.deferrable
        if self.include:
            kwargs['include'] = self.include
        if self.opclasses:
            kwargs['opclasses'] = self.opclasses
        return path, args, kwargs

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.name == other.name and
                self.index_type == other.index_type and
                self.expressions == other.expressions and
                self.condition == other.condition and
                self.deferrable == other.deferrable and
                self.include == other.include and
                self.opclasses == other.opclasses
            )
        return super().__eq__(other)

    def __repr__(self):
        return '<%s: index_type=%s, expressions=%s%s%s%s%s>' % (
            self.__class__.__qualname__,
            self.index_type,
            self.expressions,
            '' if self.condition is None else ', condition=%s' % self.condition,
            '' if self.deferrable is None else ', deferrable=%s' % self.deferrable,
            '' if not self.include else ', include=%s' % repr(self.include),
            '' if not self.opclasses else ', opclasses=%s' % repr(self.opclasses),
        )
