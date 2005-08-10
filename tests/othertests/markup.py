# Quick tests for the markup templatetags (django.contrib.markup)
#
# Requires that all supported markup modules be installed
# (http://dealmeida.net/projects/textile/, 
# http://www.freewisdom.org/projects/python-markdown,  and 
# http://docutils.sf.net/)


from django.core.template import Template, Context
import django.contrib.markup.templatetags.markup # this registers the filters

# simple examples 'cause this isn't actually testing the markup, just
# that the filters work as advertised

textile_content = """Paragraph 1

Paragraph 2 with "quotes" and @code@"""

markdown_content = """Paragraph 1

## An h2 with *italics*"""

rest_content = """Paragraph 1

Paragraph 2 with a link_

.. _link: http://www.example.com/"""

t = Template("""{{ textile_content|textile }}
----
{{ markdown_content|markdown }}
----
{{ rest_content|restructuredtext }}""")

rendered = t.render(Context(locals()))

assert rendered.strip() == """<p>Paragraph 1</p>

<p>Paragraph 2 with &#8220;quotes&#8221; and <code>code</code></p>
----
<p>Paragraph 1</p><h2>An h2 with *italics*</h2>

----
<p>Paragraph 1</p>
<p>Paragraph 2 with a <a class="reference" href="http://www.example.com/">link</a></p>"""