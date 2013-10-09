# encoding: utf8
import operator
from django.test import TestCase
from django.db.migrations.optimizer import MigrationOptimizer
from django.db import migrations
from django.db import models


class OptimizerTests(TestCase):
    """
    Tests the migration autodetector.
    """

    def optimize(self, operations):
        """
        Handy shortcut for getting results + number of loops
        """
        optimizer = MigrationOptimizer()
        return optimizer.optimize(operations), optimizer._iterations

    def assertOptimizesTo(self, operations, expected, exact=None, less_than=None):
        result, iterations = self.optimize(operations)
        self.assertEqual(expected, result)
        if exact is not None and iterations != exact:
            raise self.failureException("Optimization did not take exactly %s iterations (it took %s)" % (exact, iterations))
        if less_than is not None and iterations >= less_than:
            raise self.failureException("Optimization did not take less than %s iterations (it took %s)" % (less_than, iterations))

    def test_operation_equality(self):
        """
        Tests the equality operator on lists of operations.
        If this is broken, then the optimizer will get stuck in an
        infinite loop, so it's kind of important.
        """
        self.assertEqual(
            [migrations.DeleteModel("Test")],
            [migrations.DeleteModel("Test")],
        )
        self.assertEqual(
            [migrations.CreateModel("Test", [("name", models.CharField(max_length=255))])],
            [migrations.CreateModel("Test", [("name", models.CharField(max_length=255))])],
        )
        self.assertNotEqual(
            [migrations.CreateModel("Test", [("name", models.CharField(max_length=255))])],
            [migrations.CreateModel("Test", [("name", models.CharField(max_length=100))])],
        )
        self.assertEqual(
            [migrations.AddField("Test", "name", models.CharField(max_length=255))],
            [migrations.AddField("Test", "name", models.CharField(max_length=255))],
        )
        self.assertNotEqual(
            [migrations.AddField("Test", "name", models.CharField(max_length=255))],
            [migrations.AddField("Test", "name", models.CharField(max_length=100))],
        )
        self.assertNotEqual(
            [migrations.AddField("Test", "name", models.CharField(max_length=255))],
            [migrations.AlterField("Test", "name", models.CharField(max_length=255))],
        )

    def test_single(self):
        """
        Tests that the optimizer does nothing on a single operation,
        and that it does it in just one pass.
        """
        self.assertOptimizesTo(
            [migrations.DeleteModel("Foo")],
            [migrations.DeleteModel("Foo")],
            exact = 1,
        )

    def test_create_delete_model(self):
        """
        CreateModel and DeleteModel should collapse into nothing.
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.DeleteModel("Foo"),
            ],
            [],
        )

    def test_create_alter_delete_model(self):
        """
        CreateModel, AlterModelTable, AlterUniqueTogether, and DeleteModel should collapse into nothing.
        """
        self.assertOptimizesTo(
            [
                migrations.CreateModel("Foo", [("name", models.CharField(max_length=255))]),
                migrations.AlterModelTable("Foo", "woohoo"),
                migrations.AlterUniqueTogether("Foo", [["a", "b"]]),
                migrations.DeleteModel("Foo"),
            ],
            [],
        )
