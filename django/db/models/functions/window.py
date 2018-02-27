from django.db.models import FloatField, Func, IntegerField

__all__ = [
    'CumeDist', 'DenseRank', 'FirstValue', 'Lag', 'LastValue', 'Lead',
    'NthValue', 'Ntile', 'PercentRank', 'Rank', 'RowNumber',
]


class CumeDist(Func):
    function = 'CUME_DIST'
    name = 'CumeDist'
    output_field = FloatField()
    window_compatible = True


class DenseRank(Func):
    function = 'DENSE_RANK'
    name = 'DenseRank'
    output_field = IntegerField()
    window_compatible = True


class FirstValue(Func):
    arity = 1
    function = 'FIRST_VALUE'
    name = 'FirstValue'
    window_compatible = True


class LagLeadFunction(Func):
    window_compatible = True

    def __init__(self, expression, offset=1, default=None, **extra):
        if expression is None:
            raise ValueError(
                '%s requires a non-null source expression.' %
                self.__class__.__name__
            )
        if offset is None or offset <= 0:
            raise ValueError(
                '%s requires a positive integer for the offset.' %
                self.__class__.__name__
            )
        args = (expression, offset)
        if default is not None:
            args += (default,)
        super().__init__(*args, **extra)

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        return sources[0].output_field


class Lag(LagLeadFunction):
    function = 'LAG'
    name = 'Lag'


class LastValue(Func):
    arity = 1
    function = 'LAST_VALUE'
    name = 'LastValue'
    window_compatible = True


class Lead(LagLeadFunction):
    function = 'LEAD'
    name = 'Lead'


class NthValue(Func):
    function = 'NTH_VALUE'
    name = 'NthValue'
    window_compatible = True

    def __init__(self, expression, nth=1, **extra):
        if expression is None:
            raise ValueError('%s requires a non-null source expression.' % self.__class__.__name__)
        if nth is None or nth <= 0:
            raise ValueError('%s requires a positive integer as for nth.' % self.__class__.__name__)
        super().__init__(expression, nth, **extra)

    def _resolve_output_field(self):
        sources = self.get_source_expressions()
        return sources[0].output_field


class Ntile(Func):
    function = 'NTILE'
    name = 'Ntile'
    output_field = IntegerField()
    window_compatible = True

    def __init__(self, num_buckets=1, **extra):
        if num_buckets <= 0:
            raise ValueError('num_buckets must be greater than 0.')
        super().__init__(num_buckets, **extra)


class PercentRank(Func):
    function = 'PERCENT_RANK'
    name = 'PercentRank'
    output_field = FloatField()
    window_compatible = True


class Rank(Func):
    function = 'RANK'
    name = 'Rank'
    output_field = IntegerField()
    window_compatible = True


class RowNumber(Func):
    function = 'ROW_NUMBER'
    name = 'RowNumber'
    output_field = IntegerField()
    window_compatible = True
