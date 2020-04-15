import psycopg2

from django.db.models import (
    CharField, Expression, Field, FloatField, Func, Lookup, TextField, Value,
)
from django.db.models.expressions import CombinedExpression
from django.db.models.functions import Cast, Coalesce


class SearchVectorExact(Lookup):
    lookup_name = 'exact'

    def process_rhs(self, qn, connection):
        if not isinstance(self.rhs, (SearchQuery, CombinedSearchQuery)):
            config = getattr(self.lhs, 'config', None)
            self.rhs = SearchQuery(self.rhs, config=config)
        rhs, rhs_params = super().process_rhs(qn, connection)
        return rhs, rhs_params

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s @@ %s' % (lhs, rhs), params


class SearchVectorField(Field):

    def db_type(self, connection):
        return 'tsvector'


class SearchQueryField(Field):

    def db_type(self, connection):
        return 'tsquery'


class SearchConfig(Expression):
    def __init__(self, config):
        super().__init__()
        if not hasattr(config, 'resolve_expression'):
            config = Value(config)
        self.config = config

    @classmethod
    def from_parameter(cls, config):
        if config is None or isinstance(config, cls):
            return config
        return cls(config)

    def get_source_expressions(self):
        return [self.config]

    def set_source_expressions(self, exprs):
        self.config, = exprs

    def as_sql(self, compiler, connection):
        sql, params = compiler.compile(self.config)
        return '%s::regconfig' % sql, params


class SearchVectorCombinable:
    ADD = '||'

    def _combine(self, other, connector, reversed):
        if not isinstance(other, SearchVectorCombinable):
            raise TypeError(
                'SearchVector can only be combined with other SearchVector '
                'instances, got %s.' % type(other).__name__
            )
        if reversed:
            return CombinedSearchVector(other, connector, self, self.config)
        return CombinedSearchVector(self, connector, other, self.config)


class SearchVector(SearchVectorCombinable, Func):
    function = 'to_tsvector'
    arg_joiner = " || ' ' || "
    output_field = SearchVectorField()

    def __init__(self, *expressions, config=None, weight=None):
        super().__init__(*expressions)
        self.config = SearchConfig.from_parameter(config)
        if weight is not None and not hasattr(weight, 'resolve_expression'):
            weight = Value(weight)
        self.weight = weight

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        resolved = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        if self.config:
            resolved.config = self.config.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        return resolved

    def as_sql(self, compiler, connection, function=None, template=None):
        clone = self.copy()
        clone.set_source_expressions([
            Coalesce(
                expression
                if isinstance(expression.output_field, (CharField, TextField))
                else Cast(expression, TextField()),
                Value('')
            ) for expression in clone.get_source_expressions()
        ])
        config_sql = None
        config_params = []
        if template is None:
            if clone.config:
                config_sql, config_params = compiler.compile(clone.config)
                template = '%(function)s(%(config)s, %(expressions)s)'
            else:
                template = clone.template
        sql, params = super(SearchVector, clone).as_sql(
            compiler, connection, function=function, template=template,
            config=config_sql,
        )
        extra_params = []
        if clone.weight:
            weight_sql, extra_params = compiler.compile(clone.weight)
            sql = 'setweight({}, {})'.format(sql, weight_sql)
        return sql, config_params + params + extra_params


class CombinedSearchVector(SearchVectorCombinable, CombinedExpression):
    def __init__(self, lhs, connector, rhs, config, output_field=None):
        self.config = config
        super().__init__(lhs, connector, rhs, output_field)


class SearchQueryCombinable:
    BITAND = '&&'
    BITOR = '||'

    def _combine(self, other, connector, reversed):
        if not isinstance(other, SearchQueryCombinable):
            raise TypeError(
                'SearchQuery can only be combined with other SearchQuery '
                'instances, got %s.' % type(other).__name__
            )
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


class SearchQuery(SearchQueryCombinable, Func):
    output_field = SearchQueryField()
    SEARCH_TYPES = {
        'plain': 'plainto_tsquery',
        'phrase': 'phraseto_tsquery',
        'raw': 'to_tsquery',
        'websearch': 'websearch_to_tsquery',
    }

    def __init__(self, value, output_field=None, *, config=None, invert=False, search_type='plain'):
        self.function = self.SEARCH_TYPES.get(search_type)
        if self.function is None:
            raise ValueError("Unknown search_type argument '%s'." % search_type)
        if not hasattr(value, 'resolve_expression'):
            value = Value(value)
        expressions = (value,)
        self.config = SearchConfig.from_parameter(config)
        if self.config is not None:
            expressions = (self.config,) + expressions
        self.invert = invert
        super().__init__(*expressions, output_field=output_field)

    def as_sql(self, compiler, connection, function=None, template=None):
        sql, params = super().as_sql(compiler, connection, function, template)
        if self.invert:
            sql = '!!(%s)' % sql
        return sql, params

    def __invert__(self):
        clone = self.copy()
        clone.invert = not self.invert
        return clone

    def __str__(self):
        result = super().__str__()
        return ('~%s' % result) if self.invert else result


class CombinedSearchQuery(SearchQueryCombinable, CombinedExpression):
    def __init__(self, lhs, connector, rhs, config, output_field=None):
        self.config = config
        super().__init__(lhs, connector, rhs, output_field)

    def __str__(self):
        return '(%s)' % super().__str__()


class SearchRank(Func):
    function = 'ts_rank'
    output_field = FloatField()

    def __init__(
        self, vector, query, weights=None, normalization=None,
        cover_density=False,
    ):
        if not hasattr(vector, 'resolve_expression'):
            vector = SearchVector(vector)
        if not hasattr(query, 'resolve_expression'):
            query = SearchQuery(query)
        expressions = (vector, query)
        if weights is not None:
            if not hasattr(weights, 'resolve_expression'):
                weights = Value(weights)
            expressions = (weights,) + expressions
        if normalization is not None:
            if not hasattr(normalization, 'resolve_expression'):
                normalization = Value(normalization)
            expressions += (normalization,)
        if cover_density:
            self.function = 'ts_rank_cd'
        super().__init__(*expressions)


class SearchHeadline(Func):
    function = 'ts_headline'
    template = '%(function)s(%(expressions)s%(options)s)'
    output_field = TextField()

    def __init__(
        self, expression, query, *, config=None, start_sel=None, stop_sel=None,
        max_words=None, min_words=None, short_word=None, highlight_all=None,
        max_fragments=None, fragment_delimiter=None,
    ):
        if not hasattr(query, 'resolve_expression'):
            query = SearchQuery(query)
        options = {
            'StartSel': start_sel,
            'StopSel': stop_sel,
            'MaxWords': max_words,
            'MinWords': min_words,
            'ShortWord': short_word,
            'HighlightAll': highlight_all,
            'MaxFragments': max_fragments,
            'FragmentDelimiter': fragment_delimiter,
        }
        self.options = {
            option: value
            for option, value in options.items() if value is not None
        }
        expressions = (expression, query)
        if config is not None:
            config = SearchConfig.from_parameter(config)
            expressions = (config,) + expressions
        super().__init__(*expressions)

    def as_sql(self, compiler, connection, function=None, template=None):
        options_sql = ''
        options_params = []
        if self.options:
            # getquoted() returns a quoted bytestring of the adapted value.
            options_params.append(', '.join(
                '%s=%s' % (
                    option,
                    psycopg2.extensions.adapt(value).getquoted().decode(),
                ) for option, value in self.options.items()
            ))
            options_sql = ', %s'
        sql, params = super().as_sql(
            compiler, connection, function=function, template=template,
            options=options_sql,
        )
        return sql, params + options_params


SearchVectorField.register_lookup(SearchVectorExact)


class TrigramBase(Func):
    output_field = FloatField()

    def __init__(self, expression, string, **extra):
        if not hasattr(string, 'resolve_expression'):
            string = Value(string)
        super().__init__(expression, string, **extra)


class TrigramSimilarity(TrigramBase):
    function = 'SIMILARITY'


class TrigramDistance(TrigramBase):
    function = ''
    arg_joiner = ' <-> '


class LexemeCombinable(Expression):
    BITAND = '&'
    BITOR = '|'

    def _combine(self, other, connector, reversed, node=None):
        if not isinstance(other, LexemeCombinable):
            raise TypeError(
                'Lexeme can only be combined with other Lexemes, '
                'got {}.'.format(type(other))
            )
        if reversed:
            return CombinedLexeme(other, connector, self)
        return CombinedLexeme(self, connector, other)

    # On Combinable, these are not implemented to reduce confusion with Q. In
    # this case we are actually (ab)using them to do logical combination so
    # it's consistent with other usage in Django.
    def bitand(self, other):
        return self._combine(other, self.BITAND, False)

    def bitor(self, other):
        return self._combine(other, self.BITOR, False)

    def __or__(self, other):
        return self._combine(other, self.BITOR, False)

    def __and__(self, other):
        return self._combine(other, self.BITAND, False)


class Lexeme(LexemeCombinable, Value):
    _output_field = SearchQueryField()

    def __init__(self, value, output_field=None, *, invert=False, prefix=False, weight=None):
        self.prefix = prefix
        self.invert = invert
        self.weight = weight
        super().__init__(value, output_field=output_field)

    def as_sql(self, compiler, connection):
        param = self.value
        template = '%s'

        label = ''
        if self.prefix:
            label += '*'
        if self.weight:
            label += self.weight

        if label:
            param = '{}:{}'.format(param, label)
        if self.invert:
            param = '!{}'.format(param)
        params = [param]
        return template, params


class CombinedLexeme(LexemeCombinable):
    _output_field = SearchQueryField()

    def __init__(self, lhs, connector, rhs, output_field=None):
        super().__init__(output_field=output_field)
        self.connector = connector
        self.lhs = lhs
        self.rhs = rhs

    def as_sql(self, compiler, connection):
        value_params = []
        lsql, params = compiler.compile(self.lhs)
        value_params.extend(params)

        rsql, params = compiler.compile(self.rhs)
        value_params.extend(params)

        combined_sql = '{} {} {}'.format(lsql, self.connector, rsql)
        combined_value = combined_sql % tuple(value_params)
        return '(%s)', [combined_value]


class RawSearchQuery(SearchQueryCombinable, Expression):
    _output_field = SearchQueryField()

    def __init__(self, expressions, output_field=None, *, config=None, invert=False):
        self.config = config
        self.invert = invert
        self.expressions = expressions
        super().__init__(output_field=output_field)

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        resolved = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        if self.config:
            if not hasattr(self.config, 'resolve_expression'):
                resolved.config = Value(self.config).resolve_expression(query, allow_joins, reuse, summarize, for_save)
            else:
                resolved.config = self.config.resolve_expression(query, allow_joins, reuse, summarize, for_save)
        return resolved

    def as_sql(self, compiler, connection):
        sql, params, = compiler.compile(self.expressions)
        if self.config:
            config_sql, config_params = compiler.compile(self.config)
            template = 'to_tsquery({}::regconfig, {})'.format(config_sql, sql)
            params = params + config_params
        else:
            template = 'to_tsquery({})'.format(sql)
        if self.invert:
            template = '!!({})'.format(template)
        return template, params

    def _combine(self, other, connector, reversed, node=None):
        combined = super()._combine(other, connector, reversed, node)
        combined.output_field = SearchQueryField()
        return combined

    def __invert__(self):
        return type(self)(self.lexeme, config=self.config, invert=not self.invert)
