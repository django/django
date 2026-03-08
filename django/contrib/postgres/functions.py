from django.db.models import DateTimeField, Func, IntegerField, UUIDField


class RandomUUID(Func):
    template = "GEN_RANDOM_UUID()"
    output_field = UUIDField()


class TransactionNow(Func):
    template = "CURRENT_TIMESTAMP"
    output_field = DateTimeField()


class GenerateSeries(Func):
    """Wrapper for PostgreSQL ``generate_series()`` function.

    ``generate_series`` is a set-returning function that produces a sequence of
    values. When used in an annotation, the resulting rows are expanded; e.g.
    ``MyModel.objects.annotate(val=GenerateSeries(1, 3))`` will return three
    rows for each input row. Django needs to know that the expression is
    "set-returning" so that the ORM can evaluate it in a subquery.  This is
    indicated by ``set_returning = True``.

    The output field defaults to :class:`~django.db.models.IntegerField` but
    can be overridden if you pass a different type of values (dates/timestamps
    for example).
    """

    function = "generate_series"
    set_returning = True
    output_field = IntegerField()

    def __init__(self, *expressions, output_field=None, **extra):
        # ``generate_series`` can return integers, dates, or timestamps
        # depending on the argument types. Users may provide an explicit
        # ``output_field`` but if they don't we try to infer it from the first
        # expression. If inference fails we default to ``IntegerField``.
        if output_field is None:
            if expressions:
                first = expressions[0]
                if hasattr(first, "output_field"):
                    output_field = first.output_field
                else:
                    output_field = IntegerField()
            else:
                output_field = IntegerField()
        super().__init__(*expressions, output_field=output_field, **extra)
