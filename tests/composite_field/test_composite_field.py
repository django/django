from django.test import TestCase

from .models import User
from .utils import create_composite_test_data


class CompositeFieldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = create_composite_test_data()

    def setUp(self):
        self.user1 = self.data.users.ada

    def test_composite_alias_direct_field(self):
        inner = User.objects.filter(pk=self.user1.pk).values("email", "name")
        qs = User.objects.alias(info=inner).values("info__email", 'info__name')
        self.assertEqual(
            list(qs),
            [
                {
                    "info__email": self.user1.email,
                    "info__name": self.user1.name
                 }] * User.objects.count(),
        )
 
