from django.contrib.messages import restrictions
from django.contrib.messages.restrictions import AmountRestriction, TimeRestriction
from django.test import TestCase

from .time_provider import TestTimeProvider

restrictions.time_provider = TestTimeProvider()


class RestrictionsTest(TestCase):
    def __check_expired(self, amount_restriction, iterations_amount):
        """
        Checks whether after iterations_amount of on_display given
        restriction will become expired
        But before iterations_amount given amount_restriction must
        not indicate is_expired
        """
        for i in range(iterations_amount):
            self.assertFalse(amount_restriction.is_expired())
            amount_restriction.on_display()
        self.assertTrue(amount_restriction.is_expired())

    def test_amount_restrictions(self):
        res = AmountRestriction(4)
        self.__check_expired(res, 4)

    def test_amount_restrictions_invalid_argument(self):
        self.assertRaises(AssertionError, AmountRestriction, -1)

    def test_equal(self):
        self.assertEqual(AmountRestriction(5), AmountRestriction(5))
        self.assertFalse(AmountRestriction(1) == AmountRestriction(3))
        self.assertEqual(TimeRestriction(2), TimeRestriction(2))
        self.assertFalse(TimeRestriction(3) == TimeRestriction(4))
