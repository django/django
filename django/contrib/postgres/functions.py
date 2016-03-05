from django.db.models import DateTimeField, Func


class TransactionNow(Func):
    template = 'CURRENT_TIMESTAMP'

    def __init__(self, output_field=None, **extra):
        if output_field is None:
            output_field = DateTimeField()
        super(TransactionNow, self).__init__(output_field=output_field, **extra)
