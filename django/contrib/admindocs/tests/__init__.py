from __future__ import absolute_import, unicode_literals

from django.contrib.admindocs import utils, views
from django.db.models import fields as builtin_fields
from django.utils import unittest
from django.utils.translation import ugettext as _

from . import fields


class TestFieldType(unittest.TestCase):
    def setUp(self):
        pass

    def test_field_name(self):
        self.assertRaises(AttributeError,
                          views.get_readable_field_data_type, "NotAField")

    def test_builtin_fields(self):
        self.assertEqual(
            views.get_readable_field_data_type(builtin_fields.BooleanField()),
            _('Boolean (Either True or False)')
        )

    def test_custom_fields(self):
        self.assertEqual(
            views.get_readable_field_data_type(fields.CustomField()),
            'A custom field type'
        )
        self.assertEqual(
            views.get_readable_field_data_type(
                fields.DescriptionLackingField()),
            _('Field of type: %(field_type)s') % {
                'field_type': 'DescriptionLackingField'
            }
        )


class TestDocstrings(unittest.TestCase):
    """
    This __doc__ output is required for testing. I copied this example from
    `admindocs` documentation. (TITLE)

    Display an individual :model:`myapp.MyModel`.

    **Context**

    ``RequestContext``

    ``mymodel``
        An instance of :model:`myapp.MyModel`.

    **Template:**

    :template:`myapp/my_template.html` (DESCRIPTION)

    """

    @classmethod
    def setUpClass(cls):
        try:
            import docutils
        except ImportError:
            raise unittest.SkipTest('docutils not installed')

        super(TestDocstrings, cls).setUpClass()

    def setUp(self):
        self.title, self.description, self.metadata = utils.parse_docstring(
            self.__doc__)
        self.title_rendered = utils.parse_rst(
            self.title, 'model', 'model:admindocs')
        self.description_rendered = utils.parse_rst(
            self.description, 'model', 'model:admindocs')
        self.metadata_rendered = self.metadata
        for key in self.metadata_rendered:
            self.metadata_rendered[key] = utils.parse_rst(
                self.metadata_rendered[key], 'model', 'model:admindocs')

    def test_title_output(self):
        self.assertIn('TITLE', self.title)
        self.assertIn('TITLE', self.title_rendered)

        title_rendered = (
            '<p>This __doc__ output is required for testing. I copied this '
            'example from\n<a class="reference external" '
            'href="/admin/doc/models/admindocs/">admindocs</a> documentation. '
            '(TITLE)</p>\n')
        self.assertEqual(self.title_rendered, title_rendered)

    def test_description_output(self):
        self.assertIn('DESCRIPTION', self.description)
        self.assertIn('DESCRIPTION', self.description_rendered)

        description_rendered = (
            '<p>Display an individual <a class="reference external" '
            'href="/admin/doc/models/myapp.mymodel/">myapp.MyModel</a>.</p>\n'
            '<p><strong>Context</strong></p>\n<p><tt class="docutils literal">'
            'RequestContext</tt></p>\n<dl class="docutils">\n<dt><tt class="'
            'docutils literal">mymodel</tt></dt>\n<dd>An instance of <a class="'
            'reference external" href="/admin/doc/models/myapp.mymodel/">'
            'myapp.MyModel</a>.</dd>\n</dl>\n<p><strong>Template:</strong></p>'
            '\n<p><a class="reference external" href="/admin/doc/templates/'
            'myapp/my_template.html/">myapp/my_template.html</a> (DESCRIPTION)'
            '</p>\n')
        self.assertEqual(self.description_rendered, description_rendered)

    def test_metadata_output(self):
        self.assertDictEqual(self.metadata, {})
