from django.core.urlresolvers import reverse
from django.db import models


class TestModel(models.Model):
    name = models.CharField(max_length=100)

    def get_absolute_url(self):
        return '/testmodel/%s/' % self.id


class I18nTestModel(models.Model):
    name = models.CharField(max_length=100)

    def get_absolute_url(self):
        return reverse('i18n_testmodel', args=[self.id])
