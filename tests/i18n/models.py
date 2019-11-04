from datetime import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _


class TestModel(models.Model):
    text = models.CharField(max_length=10, default=_('Anything'))


class Company(models.Model):
    name = models.CharField(max_length=50)
    date_added = models.DateTimeField(default=datetime(1799, 1, 31, 23, 59, 59, 0))
    cents_paid = models.DecimalField(max_digits=4, decimal_places=2)
    products_delivered = models.IntegerField()

    class Meta:
        verbose_name = _('Company')
