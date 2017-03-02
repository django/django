from django.core import checks
from django.db.models import CharField, Field, FloatField, TextField
from django.db.models.expressions import CombinedExpression, Func, Value
from django.db.models.functions import Coalesce
from django.db.models.lookups import Lookup
from django.utils.encoding import force_text
from django.utils.itercompat import is_iterable
from django.utils.translation import ugettext_lazy as _


class SearchVectorExact(Lookup):
    lookup_name = 'exact'

    def process_rhs(self, qn, connection):
        if not hasattr(self.rhs, 'resolve_expression'):
            config = getattr(self.lhs, 'config', None)
            self.rhs = SearchQuery(self.rhs, config=config)
        rhs, rhs_params = super().process_rhs(qn, connection)
        return rhs, rhs_params

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s @@ %s = true' % (lhs, rhs), params


class WeightedColumn:

    WEIGHTS = ('A', 'B', 'C', 'D')

    def __init__(self, name, weight):
        self.name = name
        self.weight = weight

    def check(self, field, searchable_columns):
        errors = []
        errors.extend(self._check_column_name(field, searchable_columns))
        errors.extend(self._check_weight(field, self.WEIGHTS))
        return errors

    def _check_column_name(self, field, columns):
        if self.name not in columns:
            yield checks.Error(
                '{}.name "{}" is not one of the available columns ({})'.format(
                    self.__class__.__name__, self.name,
                    ', '.join(['"{}"'.format(c) for c in columns])
                ), obj=field, id='postgres.E110',
            )

    def _check_weight(self, field, weights):
        if self.weight not in weights:
            yield checks.Error(
                '{}.weight "{}" is not one of the available weights ({})'.format(
                    self.__class__.__name__, self.weight,
                    ', '.join(['"{}"'.format(w) for w in weights])
                ), obj=field, id='postgres.E111',
            )

    def deconstruct(self):
        path = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
        return path, [force_text(self.name), force_text(self.weight)], {}


class SearchVectorField(Field):
    description = _("PostgreSQL tsvector field")

    def __init__(self, columns=None, language=None, *args, **kwargs):
        self.columns = columns
        self.language = language
        self.language_column = kwargs.pop('language_column', None)
        self.force_update = kwargs.pop('force_update', False)
        kwargs['db_index'] = True
        kwargs['null'] = True
        super(SearchVectorField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(SearchVectorField, self).deconstruct()
        if self.columns is not None:
            kwargs['columns'] = self.columns
        if self.language is not None:
            kwargs['language'] = force_text(self.language)
        if self.language_column is not None:
            kwargs['language_column'] = force_text(self.language_column)
        if self.force_update is not False:
            kwargs['force_update'] = self.force_update
        del kwargs['db_index']
        del kwargs['null']
        return name, path, args, kwargs

    def check(self, **kwargs):
        errors = super(SearchVectorField, self).check(**kwargs)
        textual_columns = self._find_textual_columns()
        errors.extend(self._check_columns_attribute(textual_columns))
        errors.extend(self._check_language_attributes(textual_columns))
        errors.extend(self._check_force_update_attribute())
        return errors

    def _find_textual_columns(self):
        columns = []
        # PostgreSQL trigger only has access to fields in the table, so we
        # need to make sure to exclude any fields from multi-table inheritance
        for field in self.model._meta.get_fields(include_parents=False):
            # too restrictive?
            if isinstance(field, (CharField, TextField)):
                columns.append(field.column)
        return columns

    def _check_columns_attribute(self, textual_columns):
        if not self.columns:
            return
        if not textual_columns:
            yield checks.Error(
                "No textual columns available in this model for search vector indexing.",
                obj=self, id='postgres.E100',
            )
        elif not is_iterable(self.columns) or \
                not all(isinstance(wc, WeightedColumn) for wc in self.columns):
            yield checks.Error(
                "'columns' must be an iterable containing WeightedColumn instances",
                obj=self, id='postgres.E101',
            )
        else:
            for column in self.columns:
                for error in column.check(self, textual_columns):
                    yield error

    def _check_language_attributes(self, textual_columns):
        if self.columns and not any((self.language, self.language_column)):
            yield checks.Error(
                "'language' or 'language_column' is required when 'columns' is provided",
                obj=self, id='postgres.E102',
            )
            return
        if self.language and not isinstance(self.language, str):
            # can we get list of available langauges?
            yield checks.Error(
                "'language' must be a valid language",
                obj=self, id='postgres.E103',
            )
        if self.language_column and self.language_column not in textual_columns:
            yield checks.Error(
                """'language_column' "{}" is not one of the available columns ({})""".format(
                    self.name, ', '.join(['"{}"'.format(c) for c in textual_columns])
                ), obj=self, id='postgres.E104',
            )

    def _check_force_update_attribute(self):
        if self.force_update not in (None, True, False):
            yield checks.Error(
                "'force_update' must be None, True or False.",
                obj=self, id='postgres.E105',
            )

    def db_type(self, connection):
        return 'tsvector'


class SearchQueryField(Field):

    def db_type(self, connection):
        return 'tsquery'


class SearchVectorCombinable:
    ADD = '||'

    def _combine(self, other, connector, reversed, node=None):
        if not isinstance(other, SearchVectorCombinable) or not self.config == other.config:
            raise TypeError('SearchVector can only be combined with other SearchVectors')
        if reversed:
            return CombinedSearchVector(other, connector, self, self.config)
        return CombinedSearchVector(self, connector, other, self.config)


class SearchVector(SearchVectorCombinable, Func):
    function = 'to_tsvector'
    arg_joiner = " || ' ' || "
    _output_field = SearchVectorField()
    config = None

    def __init__(self, *expressions, **extra):
        super().__init__(*expressions, **extra)
        self.source_expressions = [
            Coalesce(expression, Value('')) for expression in self.source_expressions
        ]
        self.config = self.extra.get('config', self.config)
        weight = self.extra.get('weight')
        if weight is not None and not hasattr(weight, 'resolve_expression'):
            weight = Value(weight)
        self.weight = weight

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        resolved = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        if self.config:
            if not hasattr(self.config, 'resolve_expression'):
                resolved.config = Value(self.config).resolve_expression(query, allow_joins, reuse, summarize, for_save)
            else:
                resolved.config = self.config.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        return resolved

    def as_sql(self, compiler, connection, function=None, template=None):
        config_params = []
        if template is None:
            if self.config:
                config_sql, config_params = compiler.compile(self.config)
                template = "%(function)s({}::regconfig, %(expressions)s)".format(config_sql.replace('%', '%%'))
            else:
                template = self.template
        sql, params = super().as_sql(compiler, connection, function=function, template=template)
        extra_params = []
        if self.weight:
            weight_sql, extra_params = compiler.compile(self.weight)
            sql = 'setweight({}, {})'.format(sql, weight_sql)
        return sql, config_params + params + extra_params


class CombinedSearchVector(SearchVectorCombinable, CombinedExpression):
    def __init__(self, lhs, connector, rhs, config, output_field=None):
        self.config = config
        super().__init__(lhs, connector, rhs, output_field)


class SearchQueryCombinable:
    BITAND = '&&'
    BITOR = '||'

    def _combine(self, other, connector, reversed, node=None):
        if not isinstance(other, SearchQueryCombinable):
            raise TypeError(
                'SearchQuery can only be combined with other SearchQuerys, '
                'got {}.'.format(type(other))
            )
        if not self.config == other.config:
            raise TypeError("SearchQuery configs don't match.")
        if reversed:
            return CombinedSearchQuery(other, connector, self, self.config)
        return CombinedSearchQuery(self, connector, other, self.config)

    # On Combinable, these are not implemented to reduce confusion with Q. In
    # this case we are actually (ab)using them to do logical combination so
    # it's consistent with other usage in Django.
    def __or__(self, other):
        return self._combine(other, self.BITOR, False)

    def __ror__(self, other):
        return self._combine(other, self.BITOR, True)

    def __and__(self, other):
        return self._combine(other, self.BITAND, False)

    def __rand__(self, other):
        return self._combine(other, self.BITAND, True)


class SearchQuery(SearchQueryCombinable, Value):
    _output_field = SearchQueryField()

    def __init__(self, value, output_field=None, *, config=None, invert=False):
        self.config = config
        self.invert = invert
        super().__init__(value, output_field=output_field)

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        resolved = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        if self.config:
            if not hasattr(self.config, 'resolve_expression'):
                resolved.config = Value(self.config).resolve_expression(query, allow_joins, reuse, summarize, for_save)
            else:
                resolved.config = self.config.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        return resolved

    def as_sql(self, compiler, connection):
        params = [self.value]
        if self.config:
            config_sql, config_params = compiler.compile(self.config)
            template = 'plainto_tsquery({}::regconfig, %s)'.format(config_sql)
            params = config_params + [self.value]
        else:
            template = 'plainto_tsquery(%s)'
        if self.invert:
            template = '!!({})'.format(template)
        return template, params

    def _combine(self, other, connector, reversed, node=None):
        combined = super()._combine(other, connector, reversed, node)
        combined.output_field = SearchQueryField()
        return combined

    def __invert__(self):
        return type(self)(self.value, config=self.config, invert=not self.invert)


class CombinedSearchQuery(SearchQueryCombinable, CombinedExpression):
    def __init__(self, lhs, connector, rhs, config, output_field=None):
        self.config = config
        super().__init__(lhs, connector, rhs, output_field)


class SearchRank(Func):
    function = 'ts_rank'
    _output_field = FloatField()

    def __init__(self, vector, query, **extra):
        if not hasattr(vector, 'resolve_expression'):
            vector = SearchVector(vector)
        if not hasattr(query, 'resolve_expression'):
            query = SearchQuery(query)
        weights = extra.get('weights')
        if weights is not None and not hasattr(weights, 'resolve_expression'):
            weights = Value(weights)
        self.weights = weights
        super().__init__(vector, query, **extra)

    def as_sql(self, compiler, connection, function=None, template=None):
        extra_params = []
        extra_context = {}
        if template is None and self.extra.get('weights'):
            if self.weights:
                template = '%(function)s(%(weights)s, %(expressions)s)'
                weight_sql, extra_params = compiler.compile(self.weights)
                extra_context['weights'] = weight_sql
        sql, params = super().as_sql(
            compiler, connection,
            function=function, template=template, **extra_context
        )
        return sql, extra_params + params


SearchVectorField.register_lookup(SearchVectorExact)


class TrigramBase(Func):
    def __init__(self, expression, string, **extra):
        if not hasattr(string, 'resolve_expression'):
            string = Value(string)
        super().__init__(expression, string, output_field=FloatField(), **extra)


class TrigramSimilarity(TrigramBase):
    function = 'SIMILARITY'


class TrigramDistance(TrigramBase):
    function = ''
    arg_joiner = ' <-> '
