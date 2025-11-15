"""
Direct test for the reported bug:
pk setup for MTI to parent gets confused by multiple OneToOne references.

This reproduces the exact scenario from the bug report where field ordering
incorrectly affects parent link detection.
"""
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


@isolate_apps('test_ticket_parent_link_issue')
class TicketRegressionTest(SimpleTestCase):
    """
    Test the exact scenario from the bug report.
    """

    def test_failing_order_now_works(self):
        """
        This was previously failing with:
        django.core.exceptions.ImproperlyConfigured:
        Add parent_link=True to appname.Picking.origin.
        """
        class Document(models.Model):
            class Meta:
                app_label = 'test_ticket_parent_link_issue'

        # This order was failing before the fix
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
                app_label = 'test_ticket_parent_link_issue'

        # Should not raise ImproperlyConfigured
        # The parent link should be document_ptr
        self.assertEqual(Picking._meta.parents[Document].name, 'document_ptr')
        self.assertTrue(Picking._meta.parents[Document].remote_field.parent_link)
        self.assertIsNotNone(Picking._meta.pk)
        self.assertEqual(Picking._meta.pk.name, 'document_ptr')

    def test_working_order_still_works(self):
        """
        This order was working before the fix and should still work.
        """
        class Document(models.Model):
            class Meta:
                app_label = 'test_ticket_parent_link_issue'

        # This order was already working
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
                app_label = 'test_ticket_parent_link_issue'

        # Should still work correctly
        self.assertEqual(Picking._meta.parents[Document].name, 'document_ptr')
        self.assertTrue(Picking._meta.parents[Document].remote_field.parent_link)
        self.assertIsNotNone(Picking._meta.pk)
        self.assertEqual(Picking._meta.pk.name, 'document_ptr')

    def test_without_explicit_parent_link_still_fails(self):
        """
        When there are multiple OneToOneFields to parent without explicit
        parent_link=True, it should still raise an error.
        """
        with self.assertRaises(ImproperlyConfigured) as cm:
            class Document(models.Model):
                class Meta:
                    app_label = 'test_ticket_parent_link_issue'

            class Picking(Document):
                # Neither field has parent_link=True, so it's ambiguous
                field1 = models.OneToOneField(
                    Document,
                    related_name='picking1',
                    on_delete=models.PROTECT
                )
                field2 = models.OneToOneField(
                    Document,
                    related_name='picking2',
                    on_delete=models.PROTECT
                )

                class Meta:
                    app_label = 'test_ticket_parent_link_issue'

        # Should get an error asking to add parent_link=True
        self.assertIn('parent_link=True', str(cm.exception))
