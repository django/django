import decimal

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class Cash(decimal.Decimal):
    currency = 'USD'

    def __str__(self):
        s = super(Cash, self).__str__(self)
        return '%s %s' % (s, self.currency)


class CashField(models.DecimalField):
    def __init__(self, **kwargs):
        kwargs['max_digits'] = 20
        kwargs['decimal_places'] = 2
        super(CashField, self).__init__(**kwargs)

    def from_db_value(self, value, expression, connection, context):
        cash = Cash(value)
        cash.vendor = connection.vendor
        return cash


@python_2_unicode_compatible
class CashModel(models.Model):
    cash = CashField()

    def __str__(self):
        return str(self.cash)
