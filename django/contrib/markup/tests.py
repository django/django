# Quick tests for the markup templatetags (django.contrib.markup)
import re

from django.template import Template, Context, add_to_builtins
from django.utils import unittest
from django.utils.html import escape

add_to_builtins('django.contrib.markup.templatetags.markup')

try:
    import textile
except ImportError:
    textile = None

try:
    import markdown
except ImportError:
    markdown = None

try:
    import docutils
except ImportError:
    docutils = None

class Templates(unittest.TestCase):

    textile_content = """Paragraph 1

Paragraph 2 with "quotes" and @code@"""

    markdown_content = """Paragraph 1

## An h2"""

    rest_content = """Paragraph 1

Paragraph 2 with a link_

.. _link: http://www.example.com/"""


    @unittest.skipUnless(textile, 'texttile not installed')
    def test_textile(self):
        t = Template("{{ textile_content|textile }}")
        rendered = t.render(Context({'textile_content':self.textile_content})).strip()
        self.assertEqual(rendered.replace('\t', ''), """<p>Paragraph 1</p>

<p>Paragraph 2 with &#8220;quotes&#8221; and <code>code</code></p>""")

    @unittest.skipIf(textile, 'texttile is installed')
    def test_no_textile(self):
        t = Template("{{ textile_content|textile }}")
        rendered = t.render(Context({'textile_content':self.textile_content})).strip()
        self.assertEqual(rendered, escape(self.textile_content))

    @unittest.skipUnless(markdown, 'markdown not installed')
    def test_markdown(self):
        t = Template("{{ markdown_content|markdown }}")
        rendered = t.render(Context({'markdown_content':self.markdown_content})).strip()
        pattern = re.compile("""<p>Paragraph 1\s*</p>\s*<h2>\s*An h2</h2>""")
        self.assertTrue(pattern.match(rendered))

    @unittest.skipIf(markdown, 'markdown is installed')
    def test_no_markdown(self):
        t = Template("{{ markdown_content|markdown }}")
        rendered = t.render(Context({'markdown_content':self.markdown_content})).strip()
        self.assertEqual(rendered, self.markdown_content)

    @unittest.skipUnless(docutils, 'docutils not installed')
    def test_docutils(self):
        t = Template("{{ rest_content|restructuredtext }}")
        rendered = t.render(Context({'rest_content':self.rest_content})).strip()
        # Different versions of docutils return slightly different HTML
        try:
            # Docutils v0.4 and earlier
            self.assertEqual(rendered, """<p>Paragraph 1</p>
<p>Paragraph 2 with a <a class="reference" href="http://www.example.com/">link</a></p>""")
        except AssertionError, e:
            # Docutils from SVN (which will become 0.5)
            self.assertEqual(rendered, """<p>Paragraph 1</p>
<p>Paragraph 2 with a <a class="reference external" href="http://www.example.com/">link</a></p>""")

    @unittest.skipIf(docutils, 'docutils is installed')
    def test_no_docutils(self):
        t = Template("{{ rest_content|restructuredtext }}")
        rendered = t.render(Context({'rest_content':self.rest_content})).strip()
        self.assertEqual(rendered, self.rest_content)


if __name__ == '__main__':
    unittest.main()
