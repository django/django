from django.db import models
from django.utils.translation import ugettext_lazy as _

class TestModel(models.Model):
    text = models.CharField(max_length=10, default=_('Anything'))

__test__ = {'API_TESTS': '''
>>> tm = TestModel()
>>> tm.save()
'''
}

