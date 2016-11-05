import warnings

from django.db import models
from django.test import SimpleTestCase


class DeprecateIndexTogetherTests(SimpleTestCase):

    def test_deprecation_warning_is_raised(self):
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')

            class ArticleDeprecated(models.Model):
                headline = models.CharField(max_length=100)
                pub_date = models.DateTimeField()

                class Meta:
                    index_together = ['headline', 'pub_date']

        self.assertEqual(len(warns), 1)
        msg = str(warns[0].message)
        self.assertEqual(msg, "'index_together' is deprecated in favor of 'indexes'")
