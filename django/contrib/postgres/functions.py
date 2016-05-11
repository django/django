from django.db.models import DateTimeField
from django.db.models.fields import PositiveIntegerField
from django.db.models.functions import Func, Value


class TransactionNow(Func):
    template = 'CURRENT_TIMESTAMP'

    def __init__(self, output_field=None, **extra):
        if output_field is None:
            output_field = DateTimeField()
        super(TransactionNow, self).__init__(output_field=output_field, **extra)


class Levenshtein(Func):
    function = 'LEVENSHTEIN'

    def __init__(self, expression, string, **extra):
        if not hasattr(string, 'resolve_expression'):
            string = Value(string)
        super(Levenshtein, self).__init__(expression, string, output_field=PositiveIntegerField(), **extra)


class LevenshteinLessEqual(Func):
    function = 'LEVENSHTEIN_LESS_EQUAL'

    def __init__(self, expression, string, max_d, **extra):
        if not hasattr(string, 'resolve_expression'):
            string = Value(string)
        super(LevenshteinLessEqual, self).__init__(
            expression, string, max_d, output_field=PositiveIntegerField(), **extra)
