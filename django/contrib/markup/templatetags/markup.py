"""
Set of "markup" template filters for Django.  These filters transform plain text
markup syntaxes to HTML; currently there is support for:

    * Textile, which requires the PyTextile library available at
      http://dealmeida.net/projects/textile/

    * Markdown, which requires the Python-markdown library from
      http://www.freewisdom.org/projects/python-markdown

    * ReStructuredText, which requires docutils from http://docutils.sf.net/

In each case, if the required library is not installed, the filter will
silently fail and return the un-marked-up text.
"""

from django import template
from django.conf import settings
from django.utils.encoding import smart_str, force_unicode

register = template.Library()

def textile(value):
    try:
        import textile
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError, "Error in {% textile %} filter: The Python textile library isn't installed."
        return force_unicode(value)
    else:
        return force_unicode(textile.textile(smart_str(value), encoding='utf-8', output='utf-8'))

def markdown(value):
    try:
        import markdown
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError, "Error in {% markdown %} filter: The Python markdown library isn't installed."
        return force_unicode(value)
    else:
        return force_unicode(markdown.markdown(smart_str(value)))

def restructuredtext(value):
    try:
        from docutils.core import publish_parts
    except ImportError:
        if settings.DEBUG:
            raise template.TemplateSyntaxError, "Error in {% restructuredtext %} filter: The Python docutils library isn't installed."
        return force_unicode(value)
    else:
        docutils_settings = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {})
        parts = publish_parts(source=smart_str(value), writer_name="html4css1", settings_overrides=docutils_settings)
        return force_unicode(parts["fragment"])

register.filter(textile)
register.filter(markdown)
register.filter(restructuredtext)
