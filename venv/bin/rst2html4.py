#!/home/robert_texas/PycharmProjects/django/venv/bin/python

# $Id: rst2html4.py 9115 2022-07-28 17:06:24Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
A minimal front end to the Docutils Publisher, producing (X)HTML.

The output conforms to XHTML 1.0 transitional
and almost to HTML 4.01 transitional (except for closing empty tags).
"""

try:
    import locale
    locale.setlocale(locale.LC_ALL, '')
except Exception:
    pass

from docutils.core import publish_cmdline, default_description


description = ('Generates (X)HTML documents from standalone reStructuredText '
               'sources.  ' + default_description)

publish_cmdline(writer_name='html4', description=description)
