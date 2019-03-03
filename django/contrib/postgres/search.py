from django.db.models import Field, FloatField
from django.db.models.expressions import CombinedExpression, Func, Value
from django.db.models.lookups import Lookup


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


class SearchVectorField(Field):

    def db_type(self, connection):
        return 'tsvector'


class SearchQueryField(Field):

    def db_type(self, connection):
        return 'tsquery'


class SearchVectorCombinable:
    ADD = '||'

    def _combine(self, other, connector, reversed):
        if not isinstance(other, SearchVectorCombinable) or not self.config == other.config:
            raise TypeError('SearchVector can only be combined with other SearchVectors')
        if reversed:
            return CombinedSearchVector(other, connector, self, self.config)
        return CombinedSearchVector(self, connector, other, self.config)


class SearchVector(SearchVectorCombinable, Func):
    function = 'to_tsvector'
    arg_joiner = ", ' ',"
    template = '%(function)s(concat(%(expressions)s))'
    output_field = SearchVectorField()
    config = None

    def __init__(self, *expressions, **extra):
        super().__init__(*expressions, **extra)
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
                template = "%(function)s({}::regconfig, concat(%(expressions)s))".format(config_sql.replace('%', '%%'))
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

    def _combine(self, other, connector, reversed):
        if not isinstance(other, SearchQueryCombinable):
            raise TypeError(
                'SearchQuery can only be combined with other SearchQuerys, '
                'got {}.'.format(type(other))
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


class SearchQuery(SearchQueryCombinable, Value):
    output_field = SearchQueryField()
    SEARCH_TYPES = {
        'plain': 'plainto_tsquery',
        'phrase': 'phraseto_tsquery',
        'raw': 'to_tsquery',
    }

    def __init__(self, value, output_field=None, *, config=None, invert=False, search_type='plain'):
        self.config = config
        self.invert = invert
        if search_type not in self.SEARCH_TYPES:
            raise ValueError("Unknown search_type argument '%s'." % search_type)
        self.search_type = search_type
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
        function = self.SEARCH_TYPES[self.search_type]
        if self.config:
            config_sql, config_params = compiler.compile(self.config)
            template = '{}({}::regconfig, %s)'.format(function, config_sql)
            params = config_params + [self.value]
        else:
            template = '{}(%s)'.format(function)
        if self.invert:
            template = '!!({})'.format(template)
        return template, params

    def _combine(self, other, connector, reversed):
        combined = super()._combine(other, connector, reversed)
        combined.output_field = SearchQueryField()
        return combined

    def __invert__(self):
        return type(self)(self.value, config=self.config, invert=not self.invert)

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
