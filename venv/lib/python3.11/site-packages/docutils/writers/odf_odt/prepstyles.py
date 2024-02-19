#!/usr/bin/env python3

# $Id: prepstyles.py 9386 2023-05-16 14:49:31Z milde $
# Author: Dave Kuhlman <dkuhlman@rexx.com>
# Copyright: This module has been placed in the public domain.

"""
Adapt a word-processor-generated styles.odt for odtwriter use:

Drop page size specifications from styles.xml in STYLE_FILE.odt.
See https://docutils.sourceforge.io/docs/user/odt.html#page-size
"""

# Author: Michael Schutte <michi@uiae.at>

from xml.etree import ElementTree as etree

import sys
import zipfile
from tempfile import mkstemp
import shutil
import os

NAMESPACES = {
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
}


def prepstyle(filename):

    zin = zipfile.ZipFile(filename)
    styles = zin.open("styles.xml")

    root = None
    # some extra effort to preserve namespace prefixes
    for event, elem in etree.iterparse(styles, events=("start", "start-ns")):
        if event == "start-ns":
            etree.register_namespace(elem[0], elem[1])
        elif event == "start":
            if root is None:
                root = elem

    styles.close()

    for el in root.findall(".//style:page-layout-properties",
                           namespaces=NAMESPACES):
        for attr in list(el.attrib):
            if attr.startswith("{%s}" % NAMESPACES["fo"]):
                del el.attrib[attr]

    tempname = mkstemp()
    zout = zipfile.ZipFile(os.fdopen(tempname[0], "wb"), "w",
                           zipfile.ZIP_DEFLATED)

    for item in zin.infolist():
        if item.filename == "styles.xml":
            zout.writestr(item, etree.tostring(root, encoding="UTF-8"))
        else:
            zout.writestr(item, zin.read(item.filename))

    zout.close()
    zin.close()
    shutil.move(tempname[1], filename)


def main():
    args = sys.argv[1:]
    if len(args) != 1 or args[0] in ('-h', '--help'):
        print(__doc__, file=sys.stderr)
        print("Usage: %s STYLE_FILE.odt\n" % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    filename = args[0]
    prepstyle(filename)


if __name__ == '__main__':
    main()
