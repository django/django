from django.db import models
from django.test import TestCase
from django.utils.deprecation import RemovedInDjango51Warning


class IndexTogetherDeprecationTests(TestCase):
    def test_warning(self):
        msg = (
            "'index_together' is deprecated. Use 'Meta.indexes' in "
            "'model_options.MyModel' instead."
        )
        with self.assertRaisesMessage(RemovedInDjango51Warning, msg):

            class MyModel(models.Model):
                field_1 = models.IntegerField()
                field_2 = models.IntegerField()

                class Meta:
                    app_label = "model_options"
                    index_together = ["field_1", "field_2"]
