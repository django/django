# Quick tests for the markup templatetags (django.contrib.markup)
import re
import warnings

from django.template import Template, Context
from django import test
from django.utils import unittest
from django.utils.html import escape

try:
    import textile
except ImportError:
    textile = None

try:
    import markdown
    markdown_version = getattr(markdown, "version_info", 0)
except ImportError:
    markdown = None

try:
    import docutils
except ImportError:
    docutils = None

class Templates(test.TestCase):

    textile_content = """Paragraph 1

Paragraph 2 with "quotes" and @code@"""

    markdown_content = """Paragraph 1

## An h2"""

    rest_content = """Paragraph 1

Paragraph 2 with a link_

.. _link: http://www.example.com/"""

    def setUp(self):
        self.save_warnings_state()
        warnings.filterwarnings('ignore', category=DeprecationWarning, module='django.contrib.markup')

    def tearDown(self):
        self.restore_warnings_state()

    @unittest.skipUnless(textile, 'textile not installed')
    def test_textile(self):
        t = Template("{% load markup %}{{ textile_content|textile }}")
        rendered = t.render(Context({'textile_content':self.textile_content})).strip()
        self.assertEqual(rendered.replace('\t', ''), """<p>Paragraph 1</p>

<p>Paragraph 2 with &#8220;quotes&#8221; and <code>code</code></p>""")

    @unittest.skipIf(textile, 'textile is installed')
    def test_no_textile(self):
        t = Template("{% load markup %}{{ textile_content|textile }}")
        rendered = t.render(Context({'textile_content':self.textile_content})).strip()
        self.assertEqual(rendered, escape(self.textile_content))

    @unittest.skipUnless(markdown and markdown_version >= (2,1), 'markdown >= 2.1 not installed')
    def test_markdown(self):
        t = Template("{% load markup %}{{ markdown_content|markdown }}")
        rendered = t.render(Context({'markdown_content':self.markdown_content})).strip()
        pattern = re.compile("""<p>Paragraph 1\s*</p>\s*<h2>\s*An h2</h2>""")
        self.assertTrue(pattern.match(rendered))

    @unittest.skipUnless(markdown and markdown_version >= (2,1), 'markdown >= 2.1 not installed')
    def test_markdown_attribute_disable(self):
        t = Template("{% load markup %}{{ markdown_content|markdown:'safe' }}")
        markdown_content = "{@onclick=alert('hi')}some paragraph"
        rendered = t.render(Context({'markdown_content':markdown_content})).strip()
        self.assertTrue('@' in rendered)

    @unittest.skipUnless(markdown and markdown_version >= (2,1), 'markdown >= 2.1 not installed')
    def test_markdown_attribute_enable(self):
        t = Template("{% load markup %}{{ markdown_content|markdown }}")
        markdown_content = "{@onclick=alert('hi')}some paragraph"
        rendered = t.render(Context({'markdown_content':markdown_content})).strip()
        self.assertFalse('@' in rendered)

    @unittest.skipIf(markdown, 'markdown is installed')
    def test_no_markdown(self):
        t = Template("{% load markup %}{{ markdown_content|markdown }}")
        rendered = t.render(Context({'markdown_content':self.markdown_content})).strip()
        self.assertEqual(rendered, self.markdown_content)

    @unittest.skipUnless(docutils, 'docutils not installed')
    def test_docutils(self):
        t = Template("{% load markup %}{{ rest_content|restructuredtext }}")
        rendered = t.render(Context({'rest_content':self.rest_content})).strip()
        # Different versions of docutils return slightly different HTML
        try:
            # Docutils v0.4 and earlier
            self.assertEqual(rendered, """<p>Paragraph 1</p>
<p>Paragraph 2 with a <a class="reference" href="http://www.example.com/">link</a></p>""")
        except AssertionError:
            # Docutils from SVN (which will become 0.5)
            self.assertEqual(rendered, """<p>Paragraph 1</p>
<p>Paragraph 2 with a <a class="reference external" href="http://www.example.com/">link</a></p>""")

    @unittest.skipIf(docutils, 'docutils is installed')
    def test_no_docutils(self):
        t = Template("{% load markup %}{{ rest_content|restructuredtext }}")
        rendered = t.render(Context({'rest_content':self.rest_content})).strip()
        self.assertEqual(rendered, self.rest_content)
