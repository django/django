from django.db.models import DecimalField, DurationField, Func


class IntervalToSeconds(Func):
    function = ''
    template = """
    EXTRACT(day from %(expressions)s) * 86400 +
    EXTRACT(hour from %(expressions)s) * 3600 +
    EXTRACT(minute from %(expressions)s) * 60 +
    EXTRACT(second from %(expressions)s)
    """

    def __init__(self, expression, **extra):
        output_field = extra.pop('output_field', DecimalField())
        super(IntervalToSeconds, self).__init__(expression, output_field=output_field, **extra)


class SecondsToInterval(Func):
    function = 'NUMTODSINTERVAL'
    template = "%(function)s(%(expressions)s, 'SECOND')"

    def __init__(self, expression, **extra):
        output_field = extra.pop('output_field', DurationField())
        super(SecondsToInterval, self).__init__(expression, output_field=output_field, **extra)
