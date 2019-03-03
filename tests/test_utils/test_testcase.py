from django.db import IntegrityError, connections, transaction
from django.test import TestCase, skipUnlessDBFeature

from .models import Car, PossessedCar


class TestTestCase(TestCase):

    @skipUnlessDBFeature('can_defer_constraint_checks')
    @skipUnlessDBFeature('supports_foreign_keys')
    def test_fixture_teardown_checks_constraints(self):
        rollback_atomics = self._rollback_atomics
        self._rollback_atomics = lambda connection: None  # noop
        try:
            car = PossessedCar.objects.create(car_id=1, belongs_to_id=1)
            with self.assertRaises(IntegrityError), transaction.atomic():
                self._fixture_teardown()
            car.delete()
        finally:
            self._rollback_atomics = rollback_atomics

    def test_disallowed_database_connection(self):
        message = (
            "Database connections to 'other' are not allowed in this test. "
            "Add 'other' to test_utils.test_testcase.TestTestCase.databases to "
            "ensure proper test isolation and silence this failure."
        )
        with self.assertRaisesMessage(AssertionError, message):
            connections['other'].connect()
        with self.assertRaisesMessage(AssertionError, message):
            connections['other'].temporary_connection()

    def test_disallowed_database_queries(self):
        message = (
            "Database queries to 'other' are not allowed in this test. "
            "Add 'other' to test_utils.test_testcase.TestTestCase.databases to "
            "ensure proper test isolation and silence this failure."
        )
        with self.assertRaisesMessage(AssertionError, message):
            Car.objects.using('other').get()
