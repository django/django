import decimal

from django.db import models


class Cash(decimal.Decimal):
    currency = 'USD'

    def __str__(self):
        s = super().__str__(self)
        return '%s %s' % (s, self.currency)


class CashField(models.DecimalField):
    def __init__(self, **kwargs):
        kwargs['max_digits'] = 20
        kwargs['decimal_places'] = 2
        super().__init__(**kwargs)

    def from_db_value(self, value, expression, connection):
        cash = Cash(value)
        cash.vendor = connection.vendor
        return cash


class CashModel(models.Model):
    cash = CashField()

    def __str__(self):
        return str(self.cash)


class CashFieldDeprecated(CashField):
    def from_db_value(self, value, expression, connection, context):
        return super().from_db_value(value, expression, connection)


class CashModelDeprecated(models.Model):
    cash = CashFieldDeprecated()
