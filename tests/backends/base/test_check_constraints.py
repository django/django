from backends import models

from django.db import IntegrityError, connection, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature


@skipUnlessDBFeature("can_defer_constraint_checks")
class CheckDeferredConstraintTests(TransactionTestCase):
    available_apps = ["backends"]

    def test_deferred_constraint_remains_deferred(self):
        """`check_constraints` persists deferred constraints.

        The foreign key constraint on `Book.author_id` is checked on commit.
        This does not change after `check-constraints` has been called.
        """
        transaction_ = transaction.atomic()
        transaction_.__enter__()

        connection.check_constraints()

        # Creating an object with an invalid foreign key does not raise an
        # exception until the transaction commits.
        models.Book.objects.create(author_id=-1)

        with self.assertRaises(IntegrityError):
            transaction_.__exit__(None, None, None)

    @skipUnlessDBFeature("supports_deferrable_unique_constraints")
    def test_immediate_constraint_remains_immediate(self):
        """`check_constraints` persists immediate constraints.

        The unique constraint on `Author.name` is checked immediately. This
        does not change after `check-constraints` has been called.
        """
        models.DeferrableUnique.objects.create(value="Pescara")

        # Creating an author with a duplicate name immediately raises an
        # exception.
        with (
            self.assertRaises(IntegrityError),
            transaction.atomic(),  # savepoint
        ):
            models.DeferrableUnique.objects.create(value="Pescara")

        with transaction.atomic():
            connection.check_constraints()

            # Creating an author with a duplicate name immediately raises an
            # exception.
            with self.assertRaises(IntegrityError):
                models.DeferrableUnique.objects.create(value="Pescara")
