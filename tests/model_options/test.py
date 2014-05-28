from django import test
from django.db.models.options import DATA, LOCAL_ONLY, M2M

from .models import Person


class OptionsTests(test.TestCase):
    def test_data_fields(self):
        new_fields = Person._meta.get_new_fields(types=DATA, opts=LOCAL_ONLY)
        old_fields = Person._meta.fields
        self.assertEquals(old_fields, [x[1] for x in new_fields])
