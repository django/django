from __future__ import unicode_literals

from django.db import models
from django.test.testcases import SimpleTestCase
from django.utils import six
from django.utils.unittest import skipIf

from .models import CustomBaseModel


class CustomBaseTest(SimpleTestCase):

    @skipIf(six.PY3, 'test metaclass definition under Python 2')
    def test_py2_custom_base(self):
        """
        Make sure models.Model can be subclassed with a valid custom base
        using __metaclass__
        """
        try:
            class MyModel(models.Model):
                __metaclass__ = CustomBaseModel
        except Exception:
            self.fail("models.Model couldn't be subclassed with a valid "
                      "custom base using __metaclass__.")

    def test_six_custom_base(self):
        """
        Make sure models.Model can be subclassed with a valid custom base
        using `six.with_metaclass`.
        """
        try:
            class MyModel(six.with_metaclass(CustomBaseModel, models.Model)):
                pass
        except Exception:
            self.fail("models.Model couldn't be subclassed with a valid "
                      "custom base using `six.with_metaclass`.")
