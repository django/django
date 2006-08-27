# Quick tests for the markup templatetags (django.contrib.markup)

from django.template import Template, Context, add_to_builtins
import re
import unittest

add_to_builtins('django.contrib.markup.templatetags.markup')

class Templates(unittest.TestCase):
    def test_textile(self):
        try:
            import textile
        except ImportError:
            textile = None

        textile_content = """Paragraph 1

Paragraph 2 with "quotes" and @code@"""

        t = Template("{{ textile_content|textile }}")
        rendered = t.render(Context(locals())).strip()
        if textile:
            self.assertEqual(rendered, """<p>Paragraph 1</p>

<p>Paragraph 2 with &#8220;quotes&#8221; and <code>code</code></p>""")
        else:
            self.assertEqual(rendered, textile_content)

    def test_markdown(self):
        try:
            import markdown
        except ImportError:
            markdown = None

        markdown_content = """Paragraph 1

## An h2"""

        t = Template("{{ markdown_content|markdown }}")
        rendered = t.render(Context(locals())).strip()
        if markdown:
            pattern = re.compile("""<p>Paragraph 1\s*</p>\s*<h2>\s*An h2</h2>""")
            self.assert_(pattern.match(rendered))
        else:
            self.assertEqual(rendered, markdown_content)

    def test_docutils(self):
        try:
            import docutils
        except ImportError:
            docutils = None

        rest_content = """Paragraph 1

Paragraph 2 with a link_

.. _link: http://www.example.com/"""

        t = Template("{{ rest_content|restructuredtext }}")
        rendered = t.render(Context(locals())).strip()
        if docutils:
            self.assertEqual(rendered, """<p>Paragraph 1</p>
<p>Paragraph 2 with a <a class="reference" href="http://www.example.com/">link</a></p>""")
        else:
            self.assertEqual(rendered, rest_content)


if __name__ == '__main__':
    unittest.main()
