"""
Test for multi-table inheritance parent link detection with multiple OneToOneFields.
Regression test for issue where field ordering matters for parent link detection.
"""
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.test import SimpleTestCase, TestCase
from django.test.utils import isolate_apps


@isolate_apps('test_mti_parent_link_ordering')
class MultipleOneToOneFieldsTests(SimpleTestCase):
    """
    Test that parent_link detection works correctly when a child model has
    multiple OneToOneField references to the same parent, regardless of field
    declaration order.
    """

    def test_parent_link_field_before_other_field(self):
        """
        Test case where parent_link=True field is declared before
        another OneToOneField to the same parent.
        This is the working case from the bug report.
        """
        class Document(models.Model):
            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        class Picking(Document):
            origin = models.OneToOneField(
                Document,
                related_name='picking',
                on_delete=models.PROTECT
            )
            document_ptr = models.OneToOneField(
                Document,
                on_delete=models.CASCADE,
                parent_link=True,
                related_name='+'
            )

            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        # Should not raise ImproperlyConfigured
        # The document_ptr field should be recognized as the parent link
        self.assertEqual(Picking._meta.parents[Document].name, 'document_ptr')
        self.assertTrue(Picking._meta.parents[Document].remote_field.parent_link)

    def test_parent_link_field_after_other_field(self):
        """
        Test case where parent_link=True field is declared after
        another OneToOneField to the same parent.
        This was the failing case from the bug report.
        """
        class Document(models.Model):
            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        class Picking(Document):
            document_ptr = models.OneToOneField(
                Document,
                on_delete=models.CASCADE,
                parent_link=True,
                related_name='+'
            )
            origin = models.OneToOneField(
                Document,
                related_name='picking',
                on_delete=models.PROTECT
            )

            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        # Should not raise ImproperlyConfigured
        # The document_ptr field should be recognized as the parent link
        self.assertEqual(Picking._meta.parents[Document].name, 'document_ptr')
        self.assertTrue(Picking._meta.parents[Document].remote_field.parent_link)

    def test_no_explicit_parent_link_raises_error(self):
        """
        Test that when no field has parent_link=True explicitly set,
        an ImproperlyConfigured error is raised.
        """
        with self.assertRaises(ImproperlyConfigured) as cm:
            class Document(models.Model):
                class Meta:
                    app_label = 'test_mti_parent_link_ordering'

            class Picking(Document):
                origin = models.OneToOneField(
                    Document,
                    related_name='picking',
                    on_delete=models.PROTECT
                )

                class Meta:
                    app_label = 'test_mti_parent_link_ordering'

        self.assertIn('parent_link=True', str(cm.exception))

    def test_auto_created_parent_link(self):
        """
        Test that when only one OneToOneField exists without parent_link=True,
        it still auto-creates the parent link field properly.
        """
        class Document(models.Model):
            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        class Picking(Document):
            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        # Should auto-create a document_ptr field as the parent link
        self.assertIn(Document, Picking._meta.parents)
        parent_link_field = Picking._meta.parents[Document]
        self.assertIsNotNone(parent_link_field)
        self.assertTrue(parent_link_field.remote_field.parent_link)
        self.assertEqual(parent_link_field.name, 'document_ptr')

    def test_explicit_parent_link_with_custom_name(self):
        """
        Test that a custom-named parent link field works correctly.
        """
        class Document(models.Model):
            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        class Picking(Document):
            parent_doc = models.OneToOneField(
                Document,
                on_delete=models.CASCADE,
                parent_link=True,
                related_name='+'
            )
            reference = models.OneToOneField(
                Document,
                related_name='referenced_by',
                on_delete=models.PROTECT
            )

            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        # The parent_doc field should be the parent link
        self.assertEqual(Picking._meta.parents[Document].name, 'parent_doc')
        self.assertTrue(Picking._meta.parents[Document].remote_field.parent_link)

    def test_multiple_inheritance_with_multiple_fields(self):
        """
        Test multiple inheritance scenarios with multiple OneToOneFields.
        """
        class BaseA(models.Model):
            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        class BaseB(models.Model):
            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        class Child(BaseA, BaseB):
            extra_a = models.OneToOneField(
                BaseA,
                related_name='extra',
                on_delete=models.PROTECT
            )
            basea_ptr = models.OneToOneField(
                BaseA,
                on_delete=models.CASCADE,
                parent_link=True,
                related_name='+'
            )

            class Meta:
                app_label = 'test_mti_parent_link_ordering'

        # Both parents should be correctly identified
        self.assertIn(BaseA, Child._meta.parents)
        self.assertIn(BaseB, Child._meta.parents)

        # BaseA's parent link should be basea_ptr
        self.assertEqual(Child._meta.parents[BaseA].name, 'basea_ptr')
        self.assertTrue(Child._meta.parents[BaseA].remote_field.parent_link)
