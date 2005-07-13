#!/usr/bin/env python

"""
Script to build the documentation for Django from ReST -> HTML.
"""

import os
import sys
import glob
import locale
from docutils.core import publish_parts
from docutils.writers import html4css1

SETTINGS = {
    'initial_header_level': 2
}

locale.setlocale(locale.LC_ALL, '')

def build(dirs):
    writer = html4css1.Writer()
    writer.translator_class = DjangoHTMLTranslator
    for dir in dirs:
        for fname in glob.glob1(dir, "*.txt"):
            in_file = os.path.join(dir, fname)
            out_file = os.path.join(dir, os.path.splitext(fname)[0] + ".html")
            print "+++", in_file
            parts = publish_parts(
                open(in_file).read(),
                source_path=in_file,
                destination_path=out_file,
                writer=writer,
                settings_overrides={
                    'initial_header_level' : 2,
                }
            )
            open(out_file, 'w').write(parts['html_body'])

class DjangoHTMLTranslator(html4css1.HTMLTranslator):
    """Remove the damn border=1 from the standard HTML writer"""
    def visit_table(self, node):
        self.body.append(self.starttag(node, 'table', CLASS='docutils'))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        build(sys.argv[1:])
    else:
        build([os.getcwd()])
