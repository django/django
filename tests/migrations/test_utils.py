"""
Tests for migration utility functions.
"""
from django.db.migrations.operations.utils import resolve_relation
from django.test import SimpleTestCase


class ResolveRelationTests(SimpleTestCase):
    """
    Tests for the resolve_relation utility function.
    """

    def test_resolve_relation_with_mixed_case_app_label(self):
        """
        Test that resolve_relation preserves the case of app labels when
        splitting 'app_label.ModelName' strings. This is a regression test
        for a bug where mixed-case app names like 'DJ_RegLogin' were being
        incorrectly lowercased to 'dj_reglogin'.

        See: https://code.djangoproject.com/ticket/XXXXX
        """
        # Test with mixed-case app label
        app_label, model_name = resolve_relation('DJ_RegLogin.Category')
        self.assertEqual(app_label, 'DJ_RegLogin')
        self.assertEqual(model_name, 'category')

        # Test with another mixed-case app label
        app_label, model_name = resolve_relation('MyApp.Model')
        self.assertEqual(app_label, 'MyApp')
        self.assertEqual(model_name, 'model')

    def test_resolve_relation_with_lowercase_app_label(self):
        """
        Test that resolve_relation still works correctly with lowercase app labels.
        """
        app_label, model_name = resolve_relation('myapp.MyModel')
        self.assertEqual(app_label, 'myapp')
        self.assertEqual(model_name, 'mymodel')

    def test_resolve_relation_without_dot(self):
        """
        Test that resolve_relation works with unscoped model references
        when app_label is provided.
        """
        app_label, model_name = resolve_relation('Category', 'DJ_RegLogin')
        self.assertEqual(app_label, 'DJ_RegLogin')
        self.assertEqual(model_name, 'category')

    def test_resolve_relation_without_dot_missing_app_label(self):
        """
        Test that resolve_relation raises TypeError when app_label is not
        provided for unscoped model references.
        """
        with self.assertRaises(TypeError) as cm:
            resolve_relation('Category')
        self.assertIn('app_label must be provided', str(cm.exception))

    def test_resolve_relation_recursive(self):
        """
        Test that resolve_relation handles recursive relationships ('self').
        """
        app_label, model_name = resolve_relation('self', 'myapp', 'mymodel')
        self.assertEqual(app_label, 'myapp')
        self.assertEqual(model_name, 'mymodel')

    def test_resolve_relation_recursive_missing_params(self):
        """
        Test that resolve_relation raises TypeError when app_label or
        model_name is not provided for recursive relationships.
        """
        with self.assertRaises(TypeError) as cm:
            resolve_relation('self')
        self.assertIn('app_label and model_name must be provided', str(cm.exception))

    def test_resolve_relation_model_case_normalization(self):
        """
        Test that model names are always lowercased, regardless of how
        they appear in the input string.
        """
        # Model name should be lowercased
        app_label, model_name = resolve_relation('myapp.MyModel')
        self.assertEqual(model_name, 'mymodel')

        app_label, model_name = resolve_relation('MyApp.CATEGORY')
        self.assertEqual(model_name, 'category')

        # But app_label should preserve its case
        self.assertEqual(app_label, 'MyApp')
