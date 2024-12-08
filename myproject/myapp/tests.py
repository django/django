from django.test import TestCase
from django.contrib.admin.widgets import FilteredSelectMultiple

class WidgetContextTests(TestCase):
    def test_widget_context(self):
        widget = FilteredSelectMultiple(verbose_name="Test Field", is_stacked=False)
        context = widget.get_context(name="test", value=None, attrs={"id": "test_id"})
        widget_attrs = context["widget"]["attrs"]

        self.assertIn("class", widget_attrs)
        self.assertEqual(widget_attrs["class"], "selectfilter")
        self.assertEqual(widget_attrs["data-field-name"], "Test Field")
        self.assertEqual(widget_attrs["data-is-stacked"], 0)
        self.assertEqual(widget_attrs["id"], "test_id")

    def test_widget_context_stacked(self):
        widget = FilteredSelectMultiple(verbose_name="Test Field", is_stacked=True)
        context = widget.get_context(name="test", value=None, attrs={"id": "test_id"})
        widget_attrs = context["widget"]["attrs"]

        self.assertIn("class", widget_attrs)
        self.assertEqual(widget_attrs["class"], "selectfilterstacked")
        self.assertEqual(widget_attrs["data-field-name"], "Test Field")
        self.assertEqual(widget_attrs["data-is-stacked"], 1)
        self.assertEqual(widget_attrs["id"], "test_id")

    def test_widget_context_no_attrs(self):
        widget = FilteredSelectMultiple(verbose_name="Test Field", is_stacked=False)
        context = widget.get_context(name="test", value=None, attrs={})  # Use empty dict for attrs
        widget_attrs = context["widget"]["attrs"]

        self.assertIn("class", widget_attrs)
        self.assertEqual(widget_attrs["class"], "selectfilter")
        self.assertEqual(widget_attrs["data-field-name"], "Test Field")
        self.assertEqual(widget_attrs["data-is-stacked"], 0)
        self.assertEqual(widget_attrs["id"], "id_test")

    def test_widget_context_missing_name_or_attrs(self):
        widget = FilteredSelectMultiple(verbose_name="Test Field", is_stacked=False)

        # Test with name=None and id not explicitly set
        context = widget.get_context(name=None, value=None, attrs={})
        self.assertEqual(context["widget"]["attrs"]["id"], "id_None")  # Default id format for None name

        # Test with attrs=None, expecting it to default to an empty dict
        context = widget.get_context(name="test", value=None, attrs=None)
        self.assertEqual(context["widget"]["attrs"]["id"], "id_test")  # Default id format for valid name
