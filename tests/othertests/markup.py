# Quick tests for the markup templatetags (django.contrib.markup)

from django.core.template import Template, Context, add_to_builtins

add_to_builtins('django.contrib.markup.templatetags.markup')

# find out if markup modules are installed and tailor the test appropriately
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

# simple examples 'cause this isn't actually testing the markup, just
# that the filters work as advertised

### test textile

textile_content = """Paragraph 1

Paragraph 2 with "quotes" and @code@"""

t = Template("{{ textile_content|textile }}")
rendered = t.render(Context(locals())).strip()
if textile:
    assert rendered == """<p>Paragraph 1</p>

<p>Paragraph 2 with &#8220;quotes&#8221; and <code>code</code></p>"""
else:
    assert rendered == textile_content

### test markdown

markdown_content = """Paragraph 1

## An h2"""

t = Template("{{ markdown_content|markdown }}")
rendered = t.render(Context(locals())).strip()
if textile:
    assert rendered == """<p>Paragraph 1</p><h2>An h2</h2>"""
else:
    assert rendered == markdown_content

### test rest

rest_content = """Paragraph 1

Paragraph 2 with a link_

.. _link: http://www.example.com/"""

t = Template("{{ rest_content|restructuredtext }}")
rendered = t.render(Context(locals())).strip()
if docutils:
    assert rendered =="""<p>Paragraph 1</p>
<p>Paragraph 2 with a <a class="reference" href="http://www.example.com/">link</a></p>"""
else:
    assert rendered == rest_content
