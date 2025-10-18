import unittest

from django.contrib.admindocs.utils import (
    docutils_is_available,
    parse_docstring,
    parse_rst,
)
from django.test.utils import captured_stderr

from .tests import AdminDocsSimpleTestCase


@unittest.skipUnless(docutils_is_available, "no docutils installed.")
class TestUtils(AdminDocsSimpleTestCase):
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

    some_metadata: some data
    """

    def setUp(self):
        self.docstring = self.__doc__

    def test_parse_docstring(self):
        title, description, metadata = parse_docstring(self.docstring)
        docstring_title = (
            "This __doc__ output is required for testing. I copied this example from\n"
            "`admindocs` documentation. (TITLE)"
        )
        docstring_description = (
            "Display an individual :model:`myapp.MyModel`.\n\n"
            "**Context**\n\n``RequestContext``\n\n``mymodel``\n"
            "    An instance of :model:`myapp.MyModel`.\n\n"
            "**Template:**\n\n:template:`myapp/my_template.html` "
            "(DESCRIPTION)"
        )
        self.assertEqual(title, docstring_title)
        self.assertEqual(description, docstring_description)
        self.assertEqual(metadata, {"some_metadata": "some data"})

    def test_title_output(self):
        title, description, metadata = parse_docstring(self.docstring)
        title_output = parse_rst(title, "model", "model:admindocs")
        self.assertIn("TITLE", title_output)
        title_rendered = (
            "<p>This __doc__ output is required for testing. I copied this "
            'example from\n<a class="reference external" '
            'href="/admindocs/models/admindocs/">admindocs</a> documentation. '
            "(TITLE)</p>\n"
        )
        self.assertHTMLEqual(title_output, title_rendered)

    def test_description_output(self):
        title, description, metadata = parse_docstring(self.docstring)
        description_output = parse_rst(description, "model", "model:admindocs")
        description_rendered = (
            '<p>Display an individual <a class="reference external" '
            'href="/admindocs/models/myapp.mymodel/">myapp.MyModel</a>.</p>\n'
            '<p><strong>Context</strong></p>\n<p><tt class="docutils literal">'
            'RequestContext</tt></p>\n<dl class="docutils">\n<dt><tt class="'
            'docutils literal">mymodel</tt></dt>\n<dd>An instance of <a class="'
            'reference external" href="/admindocs/models/myapp.mymodel/">'
            "myapp.MyModel</a>.</dd>\n</dl>\n<p><strong>Template:</strong></p>"
            '\n<p><a class="reference external" href="/admindocs/templates/'
            'myapp/my_template.html/">myapp/my_template.html</a> (DESCRIPTION)'
            "</p>\n"
        )
        self.assertHTMLEqual(description_output, description_rendered)

    def test_initial_header_level(self):
        header = "should be h3...\n\nHeader\n------\n"
        output = parse_rst(header, "header")
        self.assertIn("<h3>Header</h3>", output)

    def test_parse_rst(self):
        """
        parse_rst() should use `cmsreference` as the default role.
        """
        markup = '<p><a class="reference external" href="/admindocs/%s">title</a></p>\n'
        self.assertEqual(parse_rst("`title`", "model"), markup % "models/title/")
        self.assertEqual(parse_rst("`title`", "view"), markup % "views/title/")
        self.assertEqual(parse_rst("`title`", "template"), markup % "templates/title/")
        self.assertEqual(parse_rst("`title`", "filter"), markup % "filters/#title")
        self.assertEqual(parse_rst("`title`", "tag"), markup % "tags/#title")

    def test_parse_rst_with_docstring_no_leading_line_feed(self):
        title, body, _ = parse_docstring("firstline\n\n    second line")
        with captured_stderr() as stderr:
            self.assertEqual(parse_rst(title, ""), "<p>firstline</p>\n")
            self.assertEqual(parse_rst(body, ""), "<p>second line</p>\n")
        self.assertEqual(stderr.getvalue(), "")

    def test_parse_rst_view_case_sensitive(self):
        source = ":view:`myapp.views.Index`"
        rendered = (
            '<p><a class="reference external" '
            'href="/admindocs/views/myapp.views.Index/">myapp.views.Index</a></p>'
        )
        self.assertHTMLEqual(parse_rst(source, "view"), rendered)

    def test_parse_rst_template_case_sensitive(self):
        source = ":template:`Index.html`"
        rendered = (
            '<p><a class="reference external" href="/admindocs/templates/Index.html/">'
            "Index.html</a></p>"
        )
        self.assertHTMLEqual(parse_rst(source, "template"), rendered)

    def test_publish_parts(self):
        """
        Django shouldn't break the default role for interpreted text
        when ``publish_parts`` is used directly, by setting it to
        ``cmsreference`` (#6681).
        """
        import docutils

        self.assertNotEqual(
            docutils.parsers.rst.roles.DEFAULT_INTERPRETED_ROLE, "cmsreference"
        )
        source = "reST, `interpreted text`, default role."
        markup = "<p>reST, <cite>interpreted text</cite>, default role.</p>\n"
        parts = docutils.core.publish_parts(source=source, writer="html4css1")
        self.assertEqual(parts["fragment"], markup)
