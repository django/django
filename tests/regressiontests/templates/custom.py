from django import test
from django import template


custom_filters = """
>>> t = template.Template("{% load custom %}{{ string|trim:5 }}")
>>> ctxt = template.Context({"string": "abcdefghijklmnopqrstuvwxyz"})
>>> t.render(ctxt)
u"abcde"
"""

