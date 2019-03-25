# $Id: __init__.py 8131 2017-07-03 22:06:53Z dkuhlman $
# Author: Dave Kuhlman <dkuhlman@rexx.com>
# Copyright: This module has been placed in the public domain.

"""
Open Document Format (ODF) Writer.

"""

VERSION = '1.0a'

__docformat__ = 'reStructuredText'


import sys
import os
import os.path
import tempfile
import zipfile
from xml.dom import minidom
import time
import re
import io
import copy
import urllib.request, urllib.error, urllib.parse
import itertools
import docutils
try:
    import locale # module missing in Jython
except ImportError:
    pass
from docutils import frontend, nodes, utils, writers, languages
from docutils.readers import standalone
from docutils.transforms import references


IMAGE_NAME_COUNTER = itertools.count()
WhichElementTree = ''
try:
    # 1. Try to use lxml.
    #from lxml import etree
    #WhichElementTree = 'lxml'
    raise ImportError('Ignoring lxml')
except ImportError as e:
    try:
        # 2. Try to use ElementTree from the Python standard library.
        from xml.etree import ElementTree as etree
        WhichElementTree = 'elementtree'
    except ImportError as e:
        try:
            # 3. Try to use a version of ElementTree installed as a separate
            #    product.
            from elementtree import ElementTree as etree
            WhichElementTree = 'elementtree'
        except ImportError as e:
            s1 = 'Must install either a version of Python containing ' \
                 'ElementTree (Python version >=2.5) or install ElementTree.'
            raise ImportError(s1)

#
# Import pygments and odtwriter pygments formatters if possible.
try:
    import pygments
    import pygments.lexers
    from .pygmentsformatter import OdtPygmentsProgFormatter, \
        OdtPygmentsLaTeXFormatter
except (ImportError, SyntaxError) as exp:
    pygments = None

# check for the Python Imaging Library
try:
    import PIL.Image
except ImportError:
    try:  # sometimes PIL modules are put in PYTHONPATH's root
        import Image
        class PIL(object): pass  # dummy wrapper
        PIL.Image = Image
    except ImportError:
        PIL = None

## import warnings
## warnings.warn('importing IPShellEmbed', UserWarning)
## from IPython.Shell import IPShellEmbed
## args = ['-pdb', '-pi1', 'In <\\#>: ', '-pi2', '   .\\D.: ',
##         '-po', 'Out<\\#>: ', '-nosep']
## ipshell = IPShellEmbed(args,
##                        banner = 'Entering IPython.  Press Ctrl-D to exit.',
##                        exit_msg = 'Leaving Interpreter, back to program.')


#
# ElementTree does not support getparent method (lxml does).
# This wrapper class and the following support functions provide
#   that support for the ability to get the parent of an element.
#
if WhichElementTree == 'elementtree':
    import weakref
    _parents = weakref.WeakKeyDictionary()
    if isinstance(etree.Element, type):
        _ElementInterface = etree.Element
    else:
        _ElementInterface = etree._ElementInterface
    class _ElementInterfaceWrapper(_ElementInterface):
        def __init__(self, tag, attrib=None):
            _ElementInterface.__init__(self, tag, attrib)
            _parents[self] = None
        def setparent(self, parent):
            _parents[self] = parent
        def getparent(self):
            return _parents[self]


#
# Constants and globals

SPACES_PATTERN = re.compile(r'( +)')
TABS_PATTERN = re.compile(r'(\t+)')
FILL_PAT1 = re.compile(r'^ +')
FILL_PAT2 = re.compile(r' {2,}')

TABLESTYLEPREFIX = 'rststyle-table-'
TABLENAMEDEFAULT = '%s0' % TABLESTYLEPREFIX
TABLEPROPERTYNAMES = ('border', 'border-top', 'border-left',
    'border-right', 'border-bottom', )

GENERATOR_DESC = 'Docutils.org/odf_odt'

NAME_SPACE_1 = 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'

CONTENT_NAMESPACE_DICT = CNSD = {
#    'office:version': '1.0',
    'chart': 'urn:oasis:names:tc:opendocument:xmlns:chart:1.0',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dom': 'http://www.w3.org/2001/xml-events',
    'dr3d': 'urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0',
    'draw': 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
    'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
    'form': 'urn:oasis:names:tc:opendocument:xmlns:form:1.0',
    'math': 'http://www.w3.org/1998/Math/MathML',
    'meta': 'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
    'number': 'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0',
    'office': NAME_SPACE_1,
    'ooo': 'http://openoffice.org/2004/office',
    'oooc': 'http://openoffice.org/2004/calc',
    'ooow': 'http://openoffice.org/2004/writer',
    'presentation': 'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',

    'script': 'urn:oasis:names:tc:opendocument:xmlns:script:1.0',
    'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'svg': 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'xforms': 'http://www.w3.org/2002/xforms',
    'xlink': 'http://www.w3.org/1999/xlink',
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    }

STYLES_NAMESPACE_DICT = SNSD = {
#    'office:version': '1.0',
    'chart': 'urn:oasis:names:tc:opendocument:xmlns:chart:1.0',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dom': 'http://www.w3.org/2001/xml-events',
    'dr3d': 'urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0',
    'draw': 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
    'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
    'form': 'urn:oasis:names:tc:opendocument:xmlns:form:1.0',
    'math': 'http://www.w3.org/1998/Math/MathML',
    'meta': 'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
    'number': 'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0',
    'office': NAME_SPACE_1,
    'presentation': 'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',
    'ooo': 'http://openoffice.org/2004/office',
    'oooc': 'http://openoffice.org/2004/calc',
    'ooow': 'http://openoffice.org/2004/writer',
    'script': 'urn:oasis:names:tc:opendocument:xmlns:script:1.0',
    'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'svg': 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'xlink': 'http://www.w3.org/1999/xlink',
    }

MANIFEST_NAMESPACE_DICT = MANNSD = {
    'manifest': 'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0',
}

META_NAMESPACE_DICT = METNSD = {
#    'office:version': '1.0',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'meta': 'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
    'office': NAME_SPACE_1,
    'ooo': 'http://openoffice.org/2004/office',
    'xlink': 'http://www.w3.org/1999/xlink',
}

#
# Attribute dictionaries for use with ElementTree (not lxml), which
#   does not support use of nsmap parameter on Element() and SubElement().

CONTENT_NAMESPACE_ATTRIB = {
    #'office:version': '1.0',
    'xmlns:chart': 'urn:oasis:names:tc:opendocument:xmlns:chart:1.0',
    'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
    'xmlns:dom': 'http://www.w3.org/2001/xml-events',
    'xmlns:dr3d': 'urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0',
    'xmlns:draw': 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
    'xmlns:fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
    'xmlns:form': 'urn:oasis:names:tc:opendocument:xmlns:form:1.0',
    'xmlns:math': 'http://www.w3.org/1998/Math/MathML',
    'xmlns:meta': 'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
    'xmlns:number': 'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0',
    'xmlns:office': NAME_SPACE_1,
    'xmlns:presentation': 'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',
    'xmlns:ooo': 'http://openoffice.org/2004/office',
    'xmlns:oooc': 'http://openoffice.org/2004/calc',
    'xmlns:ooow': 'http://openoffice.org/2004/writer',
    'xmlns:script': 'urn:oasis:names:tc:opendocument:xmlns:script:1.0',
    'xmlns:style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'xmlns:svg': 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
    'xmlns:table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'xmlns:text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'xmlns:xforms': 'http://www.w3.org/2002/xforms',
    'xmlns:xlink': 'http://www.w3.org/1999/xlink',
    'xmlns:xsd': 'http://www.w3.org/2001/XMLSchema',
    'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    }

STYLES_NAMESPACE_ATTRIB = {
    #'office:version': '1.0',
    'xmlns:chart': 'urn:oasis:names:tc:opendocument:xmlns:chart:1.0',
    'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
    'xmlns:dom': 'http://www.w3.org/2001/xml-events',
    'xmlns:dr3d': 'urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0',
    'xmlns:draw': 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
    'xmlns:fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
    'xmlns:form': 'urn:oasis:names:tc:opendocument:xmlns:form:1.0',
    'xmlns:math': 'http://www.w3.org/1998/Math/MathML',
    'xmlns:meta': 'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
    'xmlns:number': 'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0',
    'xmlns:office': NAME_SPACE_1,
    'xmlns:presentation': 'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',
    'xmlns:ooo': 'http://openoffice.org/2004/office',
    'xmlns:oooc': 'http://openoffice.org/2004/calc',
    'xmlns:ooow': 'http://openoffice.org/2004/writer',
    'xmlns:script': 'urn:oasis:names:tc:opendocument:xmlns:script:1.0',
    'xmlns:style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'xmlns:svg': 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
    'xmlns:table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'xmlns:text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'xmlns:xlink': 'http://www.w3.org/1999/xlink',
    }

MANIFEST_NAMESPACE_ATTRIB = {
    'xmlns:manifest': 'urn:oasis:names:tc:opendocument:xmlns:manifest:1.0',
}

META_NAMESPACE_ATTRIB = {
    #'office:version': '1.0',
    'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
    'xmlns:meta': 'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
    'xmlns:office': NAME_SPACE_1,
    'xmlns:ooo': 'http://openoffice.org/2004/office',
    'xmlns:xlink': 'http://www.w3.org/1999/xlink',
}


#
# Functions
#

#
# ElementTree support functions.
# In order to be able to get the parent of elements, must use these
#   instead of the functions with same name provided by ElementTree.
#
def Element(tag, attrib=None, nsmap=None, nsdict=CNSD):
    if attrib is None:
        attrib = {}
    tag, attrib = fix_ns(tag, attrib, nsdict)
    if WhichElementTree == 'lxml':
        el = etree.Element(tag, attrib, nsmap=nsmap)
    else:
        el = _ElementInterfaceWrapper(tag, attrib)
    return el

def SubElement(parent, tag, attrib=None, nsmap=None, nsdict=CNSD):
    if attrib is None:
        attrib = {}
    tag, attrib = fix_ns(tag, attrib, nsdict)
    if WhichElementTree == 'lxml':
        el = etree.SubElement(parent, tag, attrib, nsmap=nsmap)
    else:
        el = _ElementInterfaceWrapper(tag, attrib)
        parent.append(el)
        el.setparent(parent)
    return el

def fix_ns(tag, attrib, nsdict):
    nstag = add_ns(tag, nsdict)
    nsattrib = {}
    for key, val in attrib.items():
        nskey = add_ns(key, nsdict)
        nsattrib[nskey] = val
    return nstag, nsattrib

def add_ns(tag, nsdict=CNSD):
    if WhichElementTree == 'lxml':
        nstag, name = tag.split(':')
        ns = nsdict.get(nstag)
        if ns is None:
            raise RuntimeError('Invalid namespace prefix: %s' % nstag)
        tag = '{%s}%s' % (ns, name,)
    return tag

def ToString(et):
    outstream = io.StringIO()
    if sys.version_info >= (3, 2):
        et.write(outstream, encoding="unicode")
    else:
        et.write(outstream)
    s1 = outstream.getvalue()
    outstream.close()
    return s1


def escape_cdata(text):
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    ascii = ''
    for char in text:
      if ord(char) >= ord("\x7f"):
          ascii += "&#x%X;" % ( ord(char), )
      else:
          ascii += char
    return ascii



WORD_SPLIT_PAT1 = re.compile(r'\b(\w*)\b\W*')

def split_words(line):
    # We need whitespace at the end of the string for our regexpr.
    line += ' '
    words = []
    pos1 = 0
    mo = WORD_SPLIT_PAT1.search(line, pos1)
    while mo is not None:
        word = mo.groups()[0]
        words.append(word)
        pos1 = mo.end()
        mo = WORD_SPLIT_PAT1.search(line, pos1)
    return words


#
# Classes
#


class TableStyle(object):
    def __init__(self, border=None, backgroundcolor=None):
        self.border = border
        self.backgroundcolor = backgroundcolor
    def get_border_(self):
        return self.border_
    def set_border_(self, border):
        self.border_ = border
    border = property(get_border_, set_border_)
    def get_backgroundcolor_(self):
        return self.backgroundcolor_
    def set_backgroundcolor_(self, backgroundcolor):
        self.backgroundcolor_ = backgroundcolor
    backgroundcolor = property(get_backgroundcolor_, set_backgroundcolor_)

BUILTIN_DEFAULT_TABLE_STYLE = TableStyle(
    border = '0.0007in solid #000000')

#
# Information about the indentation level for lists nested inside
#   other contexts, e.g. dictionary lists.
class ListLevel(object):
    def __init__(self, level, sibling_level=True, nested_level=True):
        self.level = level
        self.sibling_level = sibling_level
        self.nested_level = nested_level
    def set_sibling(self, sibling_level): self.sibling_level = sibling_level
    def get_sibling(self): return self.sibling_level
    def set_nested(self, nested_level): self.nested_level = nested_level
    def get_nested(self): return self.nested_level
    def set_level(self, level): self.level = level
    def get_level(self): return self.level


class Writer(writers.Writer):

    MIME_TYPE = 'application/vnd.oasis.opendocument.text'
    EXTENSION = '.odt'

    supported = ('odt', )
    """Formats this writer supports."""

    default_stylesheet = 'styles' + EXTENSION

    default_stylesheet_path = utils.relative_path(
        os.path.join(os.getcwd(), 'dummy'),
        os.path.join(os.path.dirname(__file__), default_stylesheet))

    default_template = 'template.txt'

    default_template_path = utils.relative_path(
        os.path.join(os.getcwd(), 'dummy'),
        os.path.join(os.path.dirname(__file__), default_template))

    settings_spec = (
        'ODF-Specific Options',
        None,
        (
        ('Specify a stylesheet.  '
            'Default: "%s"' % default_stylesheet_path,
            ['--stylesheet'],
            {
                'default': default_stylesheet_path,
                'dest': 'stylesheet'
                }),
        ('Specify a configuration/mapping file relative to the '
            'current working '
            'directory for additional ODF options.  '
            'In particular, this file may contain a section named '
            '"Formats" that maps default style names to '
            'names to be used in the resulting output file allowing for '
            'adhering to external standards. '
            'For more info and the format of the configuration/mapping file, '
            'see the odtwriter doc.',
            ['--odf-config-file'],
            {'metavar': '<file>'}),
        ('Obfuscate email addresses to confuse harvesters while still '
            'keeping email links usable with standards-compliant browsers.',
            ['--cloak-email-addresses'],
            {'default': False,
                'action': 'store_true',
                'dest': 'cloak_email_addresses',
                'validator': frontend.validate_boolean}),
        ('Do not obfuscate email addresses.',
            ['--no-cloak-email-addresses'],
            {'default': False,
                'action': 'store_false',
                'dest': 'cloak_email_addresses',
                'validator': frontend.validate_boolean}),
        ('Specify the thickness of table borders in thousands of a cm.  '
            'Default is 35.',
            ['--table-border-thickness'],
            {'default': None,
                'validator': frontend.validate_nonnegative_int}),
        ('Add syntax highlighting in literal code blocks.',
            ['--add-syntax-highlighting'],
            {'default': False,
                'action': 'store_true',
                'dest': 'add_syntax_highlighting',
                'validator': frontend.validate_boolean}),
        ('Do not add syntax highlighting in literal code blocks. (default)',
            ['--no-syntax-highlighting'],
            {'default': False,
                'action': 'store_false',
                'dest': 'add_syntax_highlighting',
                'validator': frontend.validate_boolean}),
        ('Create sections for headers.  (default)',
            ['--create-sections'],
            {'default': True, 
                'action': 'store_true',
                'dest': 'create_sections',
                'validator': frontend.validate_boolean}),
        ('Do not create sections for headers.',
            ['--no-sections'],
            {'default': True, 
                'action': 'store_false',
                'dest': 'create_sections',
                'validator': frontend.validate_boolean}),
        ('Create links.',
            ['--create-links'],
            {'default': False,
                'action': 'store_true',
                'dest': 'create_links',
                'validator': frontend.validate_boolean}),
        ('Do not create links.  (default)',
            ['--no-links'],
            {'default': False,
                'action': 'store_false',
                'dest': 'create_links',
                'validator': frontend.validate_boolean}),
        ('Generate endnotes at end of document, not footnotes '
            'at bottom of page.',
            ['--endnotes-end-doc'],
            {'default': False,
                'action': 'store_true',
                'dest': 'endnotes_end_doc',
                'validator': frontend.validate_boolean}),
        ('Generate footnotes at bottom of page, not endnotes '
            'at end of document. (default)',
            ['--no-endnotes-end-doc'],
            {'default': False,
                'action': 'store_false',
                'dest': 'endnotes_end_doc',
                'validator': frontend.validate_boolean}),
        ('Generate a bullet list table of contents, not '
            'an ODF/oowriter table of contents.',
            ['--generate-list-toc'],
            {'default': True,
                'action': 'store_false',
                'dest': 'generate_oowriter_toc',
                'validator': frontend.validate_boolean}),
        ('Generate an ODF/oowriter table of contents, not '
            'a bullet list. (default)',
            ['--generate-oowriter-toc'],
            {'default': True,
                'action': 'store_true',
                'dest': 'generate_oowriter_toc',
                'validator': frontend.validate_boolean}),
        ('Specify the contents of an custom header line.  '
            'See odf_odt writer documentation for details '
            'about special field character sequences.',
            ['--custom-odt-header'],
            {   'default': '',
                'dest': 'custom_header',
                }),
        ('Specify the contents of an custom footer line.  '
            'See odf_odt writer documentation for details '
            'about special field character sequences.',
            ['--custom-odt-footer'],
            {   'default': '',
                'dest': 'custom_footer',
                }),
        )
        )

    settings_defaults = {
        'output_encoding_error_handler': 'xmlcharrefreplace',
        }

    relative_path_settings = (
        'stylesheet_path',
        )

    config_section = 'odf_odt writer'
    config_section_dependencies = (
        'writers',
        )

    def __init__(self):
        writers.Writer.__init__(self)
        self.translator_class = ODFTranslator

    def translate(self):
        self.settings = self.document.settings
        self.visitor = self.translator_class(self.document)
        self.visitor.retrieve_styles(self.EXTENSION)
        self.document.walkabout(self.visitor)
        self.visitor.add_doc_title()
        self.assemble_my_parts()
        self.output = self.parts['whole']

    def assemble_my_parts(self):
        """Assemble the `self.parts` dictionary.  Extend in subclasses.
        """
        writers.Writer.assemble_parts(self)
        f = tempfile.NamedTemporaryFile()
        zfile = zipfile.ZipFile(f, 'w', zipfile.ZIP_DEFLATED)
        self.write_zip_str(zfile, 'mimetype', self.MIME_TYPE,
            compress_type=zipfile.ZIP_STORED)
        content = self.visitor.content_astext()
        self.write_zip_str(zfile, 'content.xml', content)
        s1 = self.create_manifest()
        self.write_zip_str(zfile, 'META-INF/manifest.xml', s1)
        s1 = self.create_meta()
        self.write_zip_str(zfile, 'meta.xml', s1)
        s1 = self.get_stylesheet()
        # Set default language in document to be generated.
        # Language is specified by the -l/--language command line option.
        # The format is described in BCP 47.  If region is omitted, we use
        # local.normalize(ll) to obtain a region.
        language_code = None
        region_code = None
        if self.visitor.language_code:
            language_ids = self.visitor.language_code.replace('_', '-')
            language_ids = language_ids.split('-')
            # first tag is primary language tag
            language_code = language_ids[0].lower()
            # 2-letter region subtag may follow in 2nd or 3rd position
            for subtag in language_ids[1:]:
                if len(subtag) == 2 and subtag.isalpha():
                    region_code = subtag.upper()
                    break
                elif len(subtag) == 1:
                    break   # 1-letter tag is never before valid region tag
            if region_code is None:
                try:
                    rcode = locale.normalize(language_code)
                except NameError:
                    rcode = language_code
                rcode = rcode.split('_')
                if len(rcode) > 1:
                    rcode = rcode[1].split('.')
                    region_code = rcode[0]
                if region_code is None:
                    self.document.reporter.warning(
                        'invalid language-region.\n'
                        '  Could not find region with locale.normalize().\n'
                        '  Please specify both language and region (ll-RR).\n'
                        '  Examples: es-MX (Spanish, Mexico),\n'
                        '  en-AU (English, Australia).')
        # Update the style ElementTree with the language and region.
        # Note that we keep a reference to the modified node because
        # it is possible that ElementTree will throw away the Python
        # representation of the updated node if we do not.
        updated, new_dom_styles, updated_node = self.update_stylesheet(
            self.visitor.get_dom_stylesheet(), language_code, region_code)
        if updated:
            s1 = etree.tostring(new_dom_styles)
        self.write_zip_str(zfile, 'styles.xml', s1)
        self.store_embedded_files(zfile)
        self.copy_from_stylesheet(zfile)
        zfile.close()
        f.seek(0)
        whole = f.read()
        f.close()
        self.parts['whole'] = whole
        self.parts['encoding'] = self.document.settings.output_encoding
        self.parts['version'] = docutils.__version__

    def update_stylesheet(self, stylesheet_root, language_code, region_code):
        """Update xml style sheet element with language and region/country."""
        updated = False
        modified_nodes = set()
        if language_code is not None or region_code is not None:
            n1 = stylesheet_root.find(
                '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
                'styles')
            if n1 is None:
                raise RuntimeError(
                    "Cannot find 'styles' element in styles.odt/styles.xml")
            n2_nodes = n1.findall(
                '{urn:oasis:names:tc:opendocument:xmlns:style:1.0}'
                'default-style')
            if not n2_nodes:
                raise RuntimeError(
                    "Cannot find 'default-style' "
                    "element in styles.xml")
            for node in n2_nodes:
                family = node.attrib.get(
                    '{urn:oasis:names:tc:opendocument:xmlns:style:1.0}'
                    'family')
                if family == 'paragraph' or family == 'graphic':
                    n3 = node.find(
                        '{urn:oasis:names:tc:opendocument:xmlns:style:1.0}'
                        'text-properties')
                    if n3 is None:
                        raise RuntimeError(
                            "Cannot find 'text-properties' "
                            "element in styles.xml")
                    if language_code is not None:
                        n3.attrib[
                            '{urn:oasis:names:tc:opendocument:xmlns:'
                            'xsl-fo-compatible:1.0}language'] = language_code
                        n3.attrib[
                            '{urn:oasis:names:tc:opendocument:xmlns:'
                            'style:1.0}language-complex'] = language_code
                        updated = True
                        modified_nodes.add(n3)
                    if region_code is not None:
                        n3.attrib[
                            '{urn:oasis:names:tc:opendocument:xmlns:'
                            'xsl-fo-compatible:1.0}country'] = region_code
                        n3.attrib[
                            '{urn:oasis:names:tc:opendocument:xmlns:'
                            'style:1.0}country-complex'] = region_code
                        updated = True
                        modified_nodes.add(n3)
        return updated, stylesheet_root, modified_nodes

    def write_zip_str(
            self, zfile, name, bytes, compress_type=zipfile.ZIP_DEFLATED):
        localtime = time.localtime(time.time())
        zinfo = zipfile.ZipInfo(name, localtime)
        # Add some standard UNIX file access permissions (-rw-r--r--).
        zinfo.external_attr = (0x81a4 & 0xFFFF) << 16
        zinfo.compress_type = compress_type
        zfile.writestr(zinfo, bytes)

    def store_embedded_files(self, zfile):
        embedded_files = self.visitor.get_embedded_file_list()
        for source, destination in embedded_files:
            if source is None:
                continue
            try:
                zfile.write(source, destination)
            except OSError as e:
                self.document.reporter.warning(
                    "Can't open file %s." % (source, ))

    def get_settings(self):
        """
        modeled after get_stylesheet
        """
        stylespath = self.settings.stylesheet
        zfile = zipfile.ZipFile(stylespath, 'r')
        s1 = zfile.read('settings.xml')
        zfile.close()
        return s1

    def get_stylesheet(self):
        """Get the stylesheet from the visitor.
        Ask the visitor to setup the page.
        """
        s1 = self.visitor.setup_page()
        return s1

    def copy_from_stylesheet(self, outzipfile):
        """Copy images, settings, etc from the stylesheet doc into target doc.
        """
        stylespath = self.settings.stylesheet
        inzipfile = zipfile.ZipFile(stylespath, 'r')
        # Copy the styles.
        s1 = inzipfile.read('settings.xml')
        self.write_zip_str(outzipfile, 'settings.xml', s1)
        # Copy the images.
        namelist = inzipfile.namelist()
        for name in namelist:
            if name.startswith('Pictures/'):
                imageobj = inzipfile.read(name)
                outzipfile.writestr(name, imageobj)
        inzipfile.close()

    def assemble_parts(self):
        pass

    def create_manifest(self):
        if WhichElementTree == 'lxml':
            root = Element('manifest:manifest',
                nsmap=MANIFEST_NAMESPACE_DICT,
                nsdict=MANIFEST_NAMESPACE_DICT,
                )
        else:
            root = Element('manifest:manifest',
                attrib=MANIFEST_NAMESPACE_ATTRIB,
                nsdict=MANIFEST_NAMESPACE_DICT,
                )
        doc = etree.ElementTree(root)
        SubElement(root, 'manifest:file-entry', attrib={
            'manifest:media-type': self.MIME_TYPE,
            'manifest:full-path': '/',
            }, nsdict=MANNSD)
        SubElement(root, 'manifest:file-entry', attrib={
            'manifest:media-type': 'text/xml',
            'manifest:full-path': 'content.xml',
            }, nsdict=MANNSD)
        SubElement(root, 'manifest:file-entry', attrib={
            'manifest:media-type': 'text/xml',
            'manifest:full-path': 'styles.xml',
            }, nsdict=MANNSD)
        SubElement(root, 'manifest:file-entry', attrib={
            'manifest:media-type': 'text/xml',
            'manifest:full-path': 'settings.xml',
            }, nsdict=MANNSD)
        SubElement(root, 'manifest:file-entry', attrib={
            'manifest:media-type': 'text/xml',
            'manifest:full-path': 'meta.xml',
            }, nsdict=MANNSD)
        s1 = ToString(doc)
        doc = minidom.parseString(s1)
        s1 = doc.toprettyxml('  ')
        return s1

    def create_meta(self):
        if WhichElementTree == 'lxml':
            root = Element('office:document-meta',
                nsmap=META_NAMESPACE_DICT,
                nsdict=META_NAMESPACE_DICT,
                )
        else:
            root = Element('office:document-meta',
                attrib=META_NAMESPACE_ATTRIB,
                nsdict=META_NAMESPACE_DICT,
                )
        doc = etree.ElementTree(root)
        root = SubElement(root, 'office:meta', nsdict=METNSD)
        el1 = SubElement(root, 'meta:generator', nsdict=METNSD)
        el1.text = 'Docutils/rst2odf.py/%s' % (VERSION, )
        s1 = os.environ.get('USER', '')
        el1 = SubElement(root, 'meta:initial-creator', nsdict=METNSD)
        el1.text = s1
        s2 = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
        el1 = SubElement(root, 'meta:creation-date', nsdict=METNSD)
        el1.text = s2
        el1 = SubElement(root, 'dc:creator', nsdict=METNSD)
        el1.text = s1
        el1 = SubElement(root, 'dc:date', nsdict=METNSD)
        el1.text = s2
        el1 = SubElement(root, 'dc:language', nsdict=METNSD)
        el1.text = 'en-US'
        el1 = SubElement(root, 'meta:editing-cycles', nsdict=METNSD)
        el1.text = '1'
        el1 = SubElement(root, 'meta:editing-duration', nsdict=METNSD)
        el1.text = 'PT00M01S'
        title = self.visitor.get_title()
        el1 = SubElement(root, 'dc:title', nsdict=METNSD)
        if title:
            el1.text = title
        else:
            el1.text = '[no title]'
        meta_dict = self.visitor.get_meta_dict()
        keywordstr = meta_dict.get('keywords')
        if keywordstr is not None:
            keywords = split_words(keywordstr)
            for keyword in keywords:
                el1 = SubElement(root, 'meta:keyword', nsdict=METNSD)
                el1.text = keyword
        description = meta_dict.get('description')
        if description is not None:
            el1 = SubElement(root, 'dc:description', nsdict=METNSD)
            el1.text = description
        s1 = ToString(doc)
        #doc = minidom.parseString(s1)
        #s1 = doc.toprettyxml('  ')
        return s1


# class ODFTranslator(nodes.SparseNodeVisitor):
class ODFTranslator(nodes.GenericNodeVisitor):

    used_styles = (
        'attribution', 'blockindent', 'blockquote', 'blockquote-bulletitem',
        'blockquote-bulletlist', 'blockquote-enumitem', 'blockquote-enumlist',
        'bulletitem', 'bulletlist',
        'caption', 'legend',
        'centeredtextbody', 'codeblock', 'codeblock-indented',
        'codeblock-classname', 'codeblock-comment', 'codeblock-functionname',
        'codeblock-keyword', 'codeblock-name', 'codeblock-number',
        'codeblock-operator', 'codeblock-string', 'emphasis', 'enumitem',
        'enumlist', 'epigraph', 'epigraph-bulletitem', 'epigraph-bulletlist',
        'epigraph-enumitem', 'epigraph-enumlist', 'footer',
        'footnote', 'citation',
        'header', 'highlights', 'highlights-bulletitem',
        'highlights-bulletlist', 'highlights-enumitem', 'highlights-enumlist',
        'horizontalline', 'inlineliteral', 'quotation', 'rubric',
        'strong', 'table-title', 'textbody', 'tocbulletlist', 'tocenumlist',
        'title',
        'subtitle',
        'heading1',
        'heading2',
        'heading3',
        'heading4',
        'heading5',
        'heading6',
        'heading7',
        'admon-attention-hdr',
        'admon-attention-body',
        'admon-caution-hdr',
        'admon-caution-body',
        'admon-danger-hdr',
        'admon-danger-body',
        'admon-error-hdr',
        'admon-error-body',
        'admon-generic-hdr',
        'admon-generic-body',
        'admon-hint-hdr',
        'admon-hint-body',
        'admon-important-hdr',
        'admon-important-body',
        'admon-note-hdr',
        'admon-note-body',
        'admon-tip-hdr',
        'admon-tip-body',
        'admon-warning-hdr',
        'admon-warning-body',
        'tableoption',
        'tableoption.%c', 'tableoption.%c%d', 'Table%d', 'Table%d.%c',
        'Table%d.%c%d',
        'lineblock1',
        'lineblock2',
        'lineblock3',
        'lineblock4',
        'lineblock5',
        'lineblock6',
        'image', 'figureframe',
    )

    def __init__(self, document):
        #nodes.SparseNodeVisitor.__init__(self, document)
        nodes.GenericNodeVisitor.__init__(self, document)
        self.settings = document.settings
        self.language_code = self.settings.language_code
        self.language = languages.get_language(
            self.language_code,
            document.reporter)
        self.format_map = {}
        if self.settings.odf_config_file:
            from configparser import ConfigParser

            parser = ConfigParser()
            parser.read(self.settings.odf_config_file)
            for rststyle, format in parser.items("Formats"):
                if rststyle not in self.used_styles:
                    self.document.reporter.warning(
                        'Style "%s" is not a style used by odtwriter.' % (
                            rststyle, ))
                if sys.version_info.major == 2:
                    self.format_map[rststyle] = format.decode('utf-8')
        self.section_level = 0
        self.section_count = 0
        # Create ElementTree content and styles documents.
        if WhichElementTree == 'lxml':
            root = Element(
                'office:document-content',
                nsmap=CONTENT_NAMESPACE_DICT,
                )
        else:
            root = Element(
                'office:document-content',
                attrib=CONTENT_NAMESPACE_ATTRIB,
                )
        self.content_tree = etree.ElementTree(element=root)
        self.current_element = root
        SubElement(root, 'office:scripts')
        SubElement(root, 'office:font-face-decls')
        el = SubElement(root, 'office:automatic-styles')
        self.automatic_styles = el
        el = SubElement(root, 'office:body')
        el = self.generate_content_element(el)
        self.current_element = el
        self.body_text_element = el
        self.paragraph_style_stack = [self.rststyle('textbody'), ]
        self.list_style_stack = []
        self.table_count = 0
        self.column_count = ord('A') - 1
        self.trace_level = -1
        self.optiontablestyles_generated = False
        self.field_name = None
        self.field_element = None
        self.title = None
        self.image_count = 0
        self.image_style_count = 0
        self.image_dict = {}
        self.embedded_file_list = []
        self.syntaxhighlighting = 1
        self.syntaxhighlight_lexer = 'python'
        self.header_content = []
        self.footer_content = []
        self.in_header = False
        self.in_footer = False
        self.blockstyle = ''
        self.in_table_of_contents = False
        self.table_of_content_index_body = None
        self.list_level = 0
        self.def_list_level = 0
        self.footnote_ref_dict = {}
        self.footnote_list = []
        self.footnote_chars_idx = 0
        self.footnote_level = 0
        self.pending_ids = [ ]
        self.in_paragraph = False
        self.found_doc_title = False
        self.bumped_list_level_stack = []
        self.meta_dict = {}
        self.line_block_level = 0
        self.line_indent_level = 0
        self.citation_id = None
        self.style_index = 0        # use to form unique style names
        self.str_stylesheet = ''
        self.str_stylesheetcontent = ''
        self.dom_stylesheet = None
        self.table_styles = None
        self.in_citation = False

        # Keep track of nested styling classes
        self.inline_style_count_stack = []

    def get_str_stylesheet(self):
        return self.str_stylesheet

    def retrieve_styles(self, extension):
        """Retrieve the stylesheet from either a .xml file or from
        a .odt (zip) file.  Return the content as a string.
        """
        s2 = None
        stylespath = self.settings.stylesheet
        ext = os.path.splitext(stylespath)[1]
        if ext == '.xml':
            stylesfile = open(stylespath, 'r')
            s1 = stylesfile.read()
            stylesfile.close()
        elif ext == extension:
            zfile = zipfile.ZipFile(stylespath, 'r')
            s1 = zfile.read('styles.xml')
            s2 = zfile.read('content.xml')
            zfile.close()
        else:
            raise RuntimeError('stylesheet path (%s) must be %s or .xml file' %(stylespath, extension))
        self.str_stylesheet = s1
        self.str_stylesheetcontent = s2
        self.dom_stylesheet = etree.fromstring(self.str_stylesheet)
        self.dom_stylesheetcontent = etree.fromstring(self.str_stylesheetcontent)
        self.table_styles = self.extract_table_styles(s2)

    def extract_table_styles(self, styles_str):
        root = etree.fromstring(styles_str)
        table_styles = {}
        auto_styles = root.find(
            '{%s}automatic-styles' % (CNSD['office'], ))
        for stylenode in auto_styles:
            name = stylenode.get('{%s}name' % (CNSD['style'], ))
            tablename = name.split('.')[0]
            family = stylenode.get('{%s}family' % (CNSD['style'], ))
            if name.startswith(TABLESTYLEPREFIX):
                tablestyle = table_styles.get(tablename)
                if tablestyle is None:
                    tablestyle = TableStyle()
                    table_styles[tablename] = tablestyle
                if family == 'table':
                    properties = stylenode.find(
                        '{%s}table-properties' % (CNSD['style'], ))
                    property = properties.get('{%s}%s' % (CNSD['fo'],
                        'background-color', ))
                    if property is not None and property != 'none':
                        tablestyle.backgroundcolor = property
                elif family == 'table-cell':
                    properties = stylenode.find(
                        '{%s}table-cell-properties' % (CNSD['style'], ))
                    if properties is not None:
                        border = self.get_property(properties)
                        if border is not None:
                            tablestyle.border = border
        return table_styles

    def get_property(self, stylenode):
        border = None
        for propertyname in TABLEPROPERTYNAMES:
            border = stylenode.get('{%s}%s' % (CNSD['fo'], propertyname, ))
            if border is not None and border != 'none':
                return border
        return border

    def add_doc_title(self):
        text = self.settings.title
        if text:
            self.title = text
            if not self.found_doc_title:
                el = Element('text:p', attrib = {
                    'text:style-name': self.rststyle('title'),
                    })
                el.text = text
                self.body_text_element.insert(0, el)
        el = self.find_first_text_p(self.body_text_element)
        if el is not None:
            self.attach_page_style(el)

    def find_first_text_p(self, el):
        """Search the generated doc and return the first <text:p> element.
        """
        if (
                el.tag == 'text:p' or
                el.tag == 'text:h'
                ):
            return el
        elif el.getchildren():
            for child in el.getchildren():
                el1 = self.find_first_text_p(child)
                if el1 is not None:
                    return el1
            return None
        else:
            return None

    def attach_page_style(self, el):
        """Attach the default page style.

        Create an automatic-style that refers to the current style
        of this element and that refers to the default page style.
        """
        current_style = el.get('text:style-name')
        style_name = 'P1003'
        el1 = SubElement(
            self.automatic_styles, 'style:style', attrib={
                'style:name': style_name,
                'style:master-page-name': "rststyle-pagedefault",
                'style:family': "paragraph",
            }, nsdict=SNSD)
        if current_style:
            el1.set('style:parent-style-name', current_style)
        el.set('text:style-name', style_name)

    def rststyle(self, name, parameters=()):
        """
        Returns the style name to use for the given style.

        If `parameters` is given `name` must contain a matching number of
        ``%`` and is used as a format expression with `parameters` as
        the value.
        """
        name1 = name % parameters
        stylename = self.format_map.get(name1, 'rststyle-%s' % name1)
        return stylename

    def generate_content_element(self, root):
        return SubElement(root, 'office:text')

    def setup_page(self):
        self.setup_paper(self.dom_stylesheet)
        if (len(self.header_content) > 0 or len(self.footer_content) > 0 or
            self.settings.custom_header or self.settings.custom_footer):
            self.add_header_footer(self.dom_stylesheet)
        new_content = etree.tostring(self.dom_stylesheet)
        return new_content

    def get_dom_stylesheet(self):
        return self.dom_stylesheet

    def setup_paper(self, root_el):
        try:
            fin = os.popen("paperconf -s 2> /dev/null")
            w, h = list(map(float, fin.read().split()))
            fin.close()
        except:
            w, h = 612, 792     # default to Letter
        def walk(el):
            if el.tag == "{%s}page-layout-properties" % SNSD["style"] and \
                    "{%s}page-width" % SNSD["fo"] not in el.attrib:
                el.attrib["{%s}page-width" % SNSD["fo"]] = "%.3fpt" % w
                el.attrib["{%s}page-height" % SNSD["fo"]] = "%.3fpt" % h
                el.attrib["{%s}margin-left" % SNSD["fo"]] = \
                        el.attrib["{%s}margin-right" % SNSD["fo"]] = \
                        "%.3fpt" % (.1 * w)
                el.attrib["{%s}margin-top" % SNSD["fo"]] = \
                        el.attrib["{%s}margin-bottom" % SNSD["fo"]] = \
                        "%.3fpt" % (.1 * h)
            else:
                for subel in el.getchildren(): walk(subel)
        walk(root_el)

    def add_header_footer(self, root_el):
        automatic_styles = root_el.find(
            '{%s}automatic-styles' % SNSD['office'])
        path = '{%s}master-styles' % (NAME_SPACE_1, )
        master_el = root_el.find(path)
        if master_el is None:
            return
        path = '{%s}master-page' % (SNSD['style'], )
        master_el_container = master_el.findall(path)
        master_el = None
        target_attrib = '{%s}name' % (SNSD['style'], )
        target_name = self.rststyle('pagedefault')
        for el in master_el_container:
            if el.get(target_attrib) == target_name:
                master_el = el
                break
        if master_el is None:
            return
        el1 = master_el
        if self.header_content or self.settings.custom_header:
            if WhichElementTree == 'lxml':
                el2 = SubElement(el1, 'style:header', nsdict=SNSD)
            else:
                el2 = SubElement(el1, 'style:header',
                    attrib=STYLES_NAMESPACE_ATTRIB,
                    nsdict=STYLES_NAMESPACE_DICT,
                    )
            for el in self.header_content:
                attrkey = add_ns('text:style-name', nsdict=SNSD)
                el.attrib[attrkey] = self.rststyle('header')
                el2.append(el)
            if self.settings.custom_header:
                elcustom = self.create_custom_headfoot(el2,
                    self.settings.custom_header, 'header', automatic_styles)
        if self.footer_content or self.settings.custom_footer:
            if WhichElementTree == 'lxml':
                el2 = SubElement(el1, 'style:footer', nsdict=SNSD)
            else:
                el2 = SubElement(el1, 'style:footer',
                    attrib=STYLES_NAMESPACE_ATTRIB,
                    nsdict=STYLES_NAMESPACE_DICT,
                    )
            for el in self.footer_content:
                attrkey = add_ns('text:style-name', nsdict=SNSD)
                el.attrib[attrkey] = self.rststyle('footer')
                el2.append(el)
            if self.settings.custom_footer:
                elcustom = self.create_custom_headfoot(el2,
                    self.settings.custom_footer, 'footer', automatic_styles)

    code_none, code_field, code_text = list(range(3))
    field_pat = re.compile(r'%(..?)%')

    def create_custom_headfoot(self, parent, text, style_name, automatic_styles):
        parent = SubElement(parent, 'text:p', attrib={
            'text:style-name': self.rststyle(style_name),
            })
        current_element = None
        field_iter = self.split_field_specifiers_iter(text)
        for item in field_iter:
            if item[0] == ODFTranslator.code_field:
                if item[1] not in ('p', 'P', 
                    't1', 't2', 't3', 't4',
                    'd1', 'd2', 'd3', 'd4', 'd5',
                    's', 't', 'a'):
                    msg = 'bad field spec: %%%s%%' % (item[1], )
                    raise RuntimeError(msg)
                el1 = self.make_field_element(parent,
                    item[1], style_name, automatic_styles)
                if el1 is None:
                    msg = 'bad field spec: %%%s%%' % (item[1], )
                    raise RuntimeError(msg)
                else:
                    current_element = el1
            else:
                if current_element is None:
                    parent.text = item[1]
                else:
                    current_element.tail = item[1]

    def make_field_element(self, parent, text, style_name, automatic_styles):
        if text == 'p':
            el1 = SubElement(parent, 'text:page-number', attrib={
                #'text:style-name': self.rststyle(style_name),
                'text:select-page': 'current',
                })
        elif text == 'P':
            el1 = SubElement(parent, 'text:page-count', attrib={
                #'text:style-name': self.rststyle(style_name),
                })
        elif text == 't1':
            self.style_index += 1
            el1 = SubElement(parent, 'text:time', attrib={
                'text:style-name': self.rststyle(style_name),
                'text:fixed': 'true',
                'style:data-style-name': 'rst-time-style-%d' % self.style_index,
                })
            el2 = SubElement(automatic_styles, 'number:time-style', attrib={
                'style:name': 'rst-time-style-%d' % self.style_index,
                'xmlns:number': SNSD['number'],
                'xmlns:style': SNSD['style'],
                    })
            el3 = SubElement(el2, 'number:hours', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ':'
            el3 = SubElement(el2, 'number:minutes', attrib={
                    'number:style': 'long',
                    })
        elif text == 't2':
            self.style_index += 1
            el1 = SubElement(parent, 'text:time', attrib={
                'text:style-name': self.rststyle(style_name),
                'text:fixed': 'true',
                'style:data-style-name': 'rst-time-style-%d' % self.style_index,
                })
            el2 = SubElement(automatic_styles, 'number:time-style', attrib={
                'style:name': 'rst-time-style-%d' % self.style_index,
                'xmlns:number': SNSD['number'],
                'xmlns:style': SNSD['style'],
                    })
            el3 = SubElement(el2, 'number:hours', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ':'
            el3 = SubElement(el2, 'number:minutes', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ':'
            el3 = SubElement(el2, 'number:seconds', attrib={
                    'number:style': 'long',
                    })
        elif text == 't3':
            self.style_index += 1
            el1 = SubElement(parent, 'text:time', attrib={
                'text:style-name': self.rststyle(style_name),
                'text:fixed': 'true',
                'style:data-style-name': 'rst-time-style-%d' % self.style_index,
                })
            el2 = SubElement(automatic_styles, 'number:time-style', attrib={
                'style:name': 'rst-time-style-%d' % self.style_index,
                'xmlns:number': SNSD['number'],
                'xmlns:style': SNSD['style'],
                    })
            el3 = SubElement(el2, 'number:hours', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ':'
            el3 = SubElement(el2, 'number:minutes', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ' '
            el3 = SubElement(el2, 'number:am-pm')
        elif text == 't4':
            self.style_index += 1
            el1 = SubElement(parent, 'text:time', attrib={
                'text:style-name': self.rststyle(style_name),
                'text:fixed': 'true',
                'style:data-style-name': 'rst-time-style-%d' % self.style_index,
                })
            el2 = SubElement(automatic_styles, 'number:time-style', attrib={
                'style:name': 'rst-time-style-%d' % self.style_index,
                'xmlns:number': SNSD['number'],
                'xmlns:style': SNSD['style'],
                    })
            el3 = SubElement(el2, 'number:hours', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ':'
            el3 = SubElement(el2, 'number:minutes', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ':'
            el3 = SubElement(el2, 'number:seconds', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ' '
            el3 = SubElement(el2, 'number:am-pm')
        elif text == 'd1':
            self.style_index += 1
            el1 = SubElement(parent, 'text:date', attrib={
                'text:style-name': self.rststyle(style_name),
                'style:data-style-name': 'rst-date-style-%d' % self.style_index,
                })
            el2 = SubElement(automatic_styles, 'number:date-style', attrib={
                'style:name': 'rst-date-style-%d' % self.style_index,
                'number:automatic-order': 'true',
                'xmlns:number': SNSD['number'],
                'xmlns:style': SNSD['style'],
                    })
            el3 = SubElement(el2, 'number:month', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = '/'
            el3 = SubElement(el2, 'number:day', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = '/'
            el3 = SubElement(el2, 'number:year')
        elif text == 'd2':
            self.style_index += 1
            el1 = SubElement(parent, 'text:date', attrib={
                'text:style-name': self.rststyle(style_name),
                'style:data-style-name': 'rst-date-style-%d' % self.style_index,
                })
            el2 = SubElement(automatic_styles, 'number:date-style', attrib={
                'style:name': 'rst-date-style-%d' % self.style_index,
                'number:automatic-order': 'true',
                'xmlns:number': SNSD['number'],
                'xmlns:style': SNSD['style'],
                    })
            el3 = SubElement(el2, 'number:month', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = '/'
            el3 = SubElement(el2, 'number:day', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = '/'
            el3 = SubElement(el2, 'number:year', attrib={
                    'number:style': 'long',
                    })
        elif text == 'd3':
            self.style_index += 1
            el1 = SubElement(parent, 'text:date', attrib={
                'text:style-name': self.rststyle(style_name),
                'style:data-style-name': 'rst-date-style-%d' % self.style_index,
                })
            el2 = SubElement(automatic_styles, 'number:date-style', attrib={
                'style:name': 'rst-date-style-%d' % self.style_index,
                'number:automatic-order': 'true',
                'xmlns:number': SNSD['number'],
                'xmlns:style': SNSD['style'],
                    })
            el3 = SubElement(el2, 'number:month', attrib={
                    'number:textual': 'true',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ' '
            el3 = SubElement(el2, 'number:day', attrib={
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ', '
            el3 = SubElement(el2, 'number:year', attrib={
                    'number:style': 'long',
                    })
        elif text == 'd4':
            self.style_index += 1
            el1 = SubElement(parent, 'text:date', attrib={
                'text:style-name': self.rststyle(style_name),
                'style:data-style-name': 'rst-date-style-%d' % self.style_index,
                })
            el2 = SubElement(automatic_styles, 'number:date-style', attrib={
                'style:name': 'rst-date-style-%d' % self.style_index,
                'number:automatic-order': 'true',
                'xmlns:number': SNSD['number'],
                'xmlns:style': SNSD['style'],
                    })
            el3 = SubElement(el2, 'number:month', attrib={
                    'number:textual': 'true',
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ' '
            el3 = SubElement(el2, 'number:day', attrib={
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = ', '
            el3 = SubElement(el2, 'number:year', attrib={
                    'number:style': 'long',
                    })
        elif text == 'd5':
            self.style_index += 1
            el1 = SubElement(parent, 'text:date', attrib={
                'text:style-name': self.rststyle(style_name),
                'style:data-style-name': 'rst-date-style-%d' % self.style_index,
                })
            el2 = SubElement(automatic_styles, 'number:date-style', attrib={
                'style:name': 'rst-date-style-%d' % self.style_index,
                'xmlns:number': SNSD['number'],
                'xmlns:style': SNSD['style'],
                    })
            el3 = SubElement(el2, 'number:year', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = '-'
            el3 = SubElement(el2, 'number:month', attrib={
                    'number:style': 'long',
                    })
            el3 = SubElement(el2, 'number:text')
            el3.text = '-'
            el3 = SubElement(el2, 'number:day', attrib={
                    'number:style': 'long',
                    })
        elif text == 's':
            el1 = SubElement(parent, 'text:subject', attrib={
                'text:style-name': self.rststyle(style_name),
                })
        elif text == 't':
            el1 = SubElement(parent, 'text:title', attrib={
                'text:style-name': self.rststyle(style_name),
                })
        elif text == 'a':
            el1 = SubElement(parent, 'text:author-name', attrib={
                'text:fixed': 'false',
                })
        else:
            el1 = None
        return el1

    def split_field_specifiers_iter(self, text):
        pos1 = 0
        pos_end = len(text)
        while True:
            mo = ODFTranslator.field_pat.search(text, pos1)
            if mo:
                pos2 = mo.start()
                if pos2 > pos1:
                    yield (ODFTranslator.code_text, text[pos1:pos2])
                yield (ODFTranslator.code_field, mo.group(1))
                pos1 = mo.end()
            else:
                break
        trailing = text[pos1:]
        if trailing:
            yield (ODFTranslator.code_text, trailing)


    def astext(self):
        root = self.content_tree.getroot()
        et = etree.ElementTree(root)
        s1 = ToString(et)
        return s1

    def content_astext(self):
        return self.astext()

    def set_title(self, title): self.title = title
    def get_title(self): return self.title
    def set_embedded_file_list(self, embedded_file_list):
        self.embedded_file_list = embedded_file_list
    def get_embedded_file_list(self): return self.embedded_file_list
    def get_meta_dict(self): return self.meta_dict

    def process_footnotes(self):
        for node, el1 in self.footnote_list:
            backrefs = node.attributes.get('backrefs', [])
            first = True
            for ref in backrefs:
                el2 = self.footnote_ref_dict.get(ref)
                if el2 is not None:
                    if first:
                        first = False
                        el3 = copy.deepcopy(el1)
                        el2.append(el3)
                    else:
                        children = el2.getchildren()
                        if len(children) > 0: #  and 'id' in el2.attrib:
                            child = children[0]
                            ref1 = child.text
                            attribkey = add_ns('text:id', nsdict=SNSD)
                            id1 = el2.get(attribkey, 'footnote-error')
                            if id1 is None:
                                id1 = ''
                            tag = add_ns('text:note-ref', nsdict=SNSD)
                            el2.tag = tag
                            if self.settings.endnotes_end_doc:
                                note_class = 'endnote'
                            else:
                                note_class = 'footnote'
                            el2.attrib.clear()
                            attribkey = add_ns('text:note-class', nsdict=SNSD)
                            el2.attrib[attribkey] = note_class
                            attribkey = add_ns('text:ref-name', nsdict=SNSD)
                            el2.attrib[attribkey] = id1
                            attribkey = add_ns('text:reference-format', nsdict=SNSD)
                            el2.attrib[attribkey] = 'page'
                            el2.text = ref1

    #
    # Utility methods

    def append_child(self, tag, attrib=None, parent=None):
        if parent is None:
            parent = self.current_element
        if attrib is None:
            el = SubElement(parent, tag)
        else:
            el = SubElement(parent, tag, attrib)
        return el

    def append_p(self, style, text=None):
        result = self.append_child('text:p', attrib={
                'text:style-name': self.rststyle(style)})
        self.append_pending_ids(result)
        if text is not None:
            result.text = text
        return result

    def append_pending_ids(self, el):
        if self.settings.create_links:
            for id in self.pending_ids:
                SubElement(el, 'text:reference-mark', attrib={
                        'text:name': id})
        self.pending_ids = [ ]

    def set_current_element(self, el):
        self.current_element = el

    def set_to_parent(self):
        self.current_element = self.current_element.getparent()

    def generate_labeled_block(self, node, label):
        label = '%s:' % (self.language.labels[label], )
        el = self.append_p('textbody')
        el1 = SubElement(el, 'text:span',
            attrib={'text:style-name': self.rststyle('strong')})
        el1.text = label
        el = self.append_p('blockindent')
        return el

    def generate_labeled_line(self, node, label):
        label = '%s:' % (self.language.labels[label], )
        el = self.append_p('textbody')
        el1 = SubElement(el, 'text:span',
            attrib={'text:style-name': self.rststyle('strong')})
        el1.text = label
        el1.tail = node.astext()
        return el

    def encode(self, text):
        text = text.replace('\u00a0', " ")
        return text

    #
    # Visitor functions
    #
    # In alphabetic order, more or less.
    #   See docutils.docutils.nodes.node_class_names.
    #

    def dispatch_visit(self, node):
        """Override to catch basic attributes which many nodes have."""
        self.handle_basic_atts(node)
        nodes.GenericNodeVisitor.dispatch_visit(self, node)

    def handle_basic_atts(self, node):
        if isinstance(node, nodes.Element) and node['ids']:
            self.pending_ids += node['ids']

    def default_visit(self, node):
        self.document.reporter.warning('missing visit_%s' % (node.tagname, ))

    def default_departure(self, node):
        self.document.reporter.warning('missing depart_%s' % (node.tagname, ))

    def visit_Text(self, node):
        # Skip nodes whose text has been processed in parent nodes.
        if isinstance(node.parent, docutils.nodes.literal_block):
            return
        text = node.astext()
        # Are we in mixed content?  If so, add the text to the
        #   etree tail of the previous sibling element.
        if len(self.current_element.getchildren()) > 0:
            if self.current_element.getchildren()[-1].tail:
                self.current_element.getchildren()[-1].tail += text
            else:
                self.current_element.getchildren()[-1].tail = text
        else:
            if self.current_element.text:
                self.current_element.text += text
            else:
                self.current_element.text = text

    def depart_Text(self, node):
        pass

    #
    # Pre-defined fields
    #

    def visit_address(self, node):
        el = self.generate_labeled_block(node, 'address')
        self.set_current_element(el)

    def depart_address(self, node):
        self.set_to_parent()

    def visit_author(self, node):
        if isinstance(node.parent, nodes.authors):
            el = self.append_p('blockindent')
        else:
            el = self.generate_labeled_block(node, 'author')
        self.set_current_element(el)

    def depart_author(self, node):
        self.set_to_parent()

    def visit_authors(self, node):
        label = '%s:' % (self.language.labels['authors'], )
        el = self.append_p('textbody')
        el1 = SubElement(el, 'text:span',
            attrib={'text:style-name': self.rststyle('strong')})
        el1.text = label

    def depart_authors(self, node):
        pass

    def visit_contact(self, node):
        el = self.generate_labeled_block(node, 'contact')
        self.set_current_element(el)

    def depart_contact(self, node):
        self.set_to_parent()

    def visit_copyright(self, node):
        el = self.generate_labeled_block(node, 'copyright')
        self.set_current_element(el)

    def depart_copyright(self, node):
        self.set_to_parent()

    def visit_date(self, node):
        self.generate_labeled_line(node, 'date')

    def depart_date(self, node):
        pass

    def visit_organization(self, node):
        el = self.generate_labeled_block(node, 'organization')
        self.set_current_element(el)

    def depart_organization(self, node):
        self.set_to_parent()

    def visit_status(self, node):
        el = self.generate_labeled_block(node, 'status')
        self.set_current_element(el)

    def depart_status(self, node):
        self.set_to_parent()

    def visit_revision(self, node):
        el = self.generate_labeled_line(node, 'revision')

    def depart_revision(self, node):
        pass

    def visit_version(self, node):
        el = self.generate_labeled_line(node, 'version')
        #self.set_current_element(el)

    def depart_version(self, node):
        #self.set_to_parent()
        pass

    def visit_attribution(self, node):
        el = self.append_p('attribution', node.astext())

    def depart_attribution(self, node):
        pass

    def visit_block_quote(self, node):
        if 'epigraph' in node.attributes['classes']:
            self.paragraph_style_stack.append(self.rststyle('epigraph'))
            self.blockstyle = self.rststyle('epigraph')
        elif 'highlights' in node.attributes['classes']:
            self.paragraph_style_stack.append(self.rststyle('highlights'))
            self.blockstyle = self.rststyle('highlights')
        else:
            self.paragraph_style_stack.append(self.rststyle('blockquote'))
            self.blockstyle = self.rststyle('blockquote')
        self.line_indent_level += 1

    def depart_block_quote(self, node):
        self.paragraph_style_stack.pop()
        self.blockstyle = ''
        self.line_indent_level -= 1

    def visit_bullet_list(self, node):
        self.list_level +=1
        if self.in_table_of_contents:
            if self.settings.generate_oowriter_toc:
                pass
            else:
                if 'classes' in node and \
                        'auto-toc' in node.attributes['classes']:
                    el = SubElement(self.current_element, 'text:list', attrib={
                        'text:style-name': self.rststyle('tocenumlist'),
                        })
                    self.list_style_stack.append(self.rststyle('enumitem'))
                else:
                    el = SubElement(self.current_element, 'text:list', attrib={
                        'text:style-name': self.rststyle('tocbulletlist'),
                        })
                    self.list_style_stack.append(self.rststyle('bulletitem'))
                self.set_current_element(el)
        else:
            if self.blockstyle == self.rststyle('blockquote'):
                el = SubElement(self.current_element, 'text:list', attrib={
                    'text:style-name': self.rststyle('blockquote-bulletlist'),
                    })
                self.list_style_stack.append(
                    self.rststyle('blockquote-bulletitem'))
            elif self.blockstyle == self.rststyle('highlights'):
                el = SubElement(self.current_element, 'text:list', attrib={
                    'text:style-name': self.rststyle('highlights-bulletlist'),
                    })
                self.list_style_stack.append(
                    self.rststyle('highlights-bulletitem'))
            elif self.blockstyle == self.rststyle('epigraph'):
                el = SubElement(self.current_element, 'text:list', attrib={
                    'text:style-name': self.rststyle('epigraph-bulletlist'),
                    })
                self.list_style_stack.append(
                    self.rststyle('epigraph-bulletitem'))
            else:
                el = SubElement(self.current_element, 'text:list', attrib={
                    'text:style-name': self.rststyle('bulletlist'),
                    })
                self.list_style_stack.append(self.rststyle('bulletitem'))
            self.set_current_element(el)

    def depart_bullet_list(self, node):
        if self.in_table_of_contents:
            if self.settings.generate_oowriter_toc:
                pass
            else:
                self.set_to_parent()
                self.list_style_stack.pop()
        else:
            self.set_to_parent()
            self.list_style_stack.pop()
        self.list_level -=1

    def visit_caption(self, node):
        raise nodes.SkipChildren()
        pass

    def depart_caption(self, node):
        pass

    def visit_comment(self, node):
        el = self.append_p('textbody')
        el1 =  SubElement(el, 'office:annotation', attrib={})
        el2 =  SubElement(el1, 'dc:creator', attrib={})
        s1 = os.environ.get('USER', '')
        el2.text = s1
        el2 =  SubElement(el1, 'text:p', attrib={})
        el2.text = node.astext()

    def depart_comment(self, node):
        pass

    def visit_compound(self, node):
        # The compound directive currently receives no special treatment.
        pass

    def depart_compound(self, node):
        pass

    def visit_container(self, node):
        styles = node.attributes.get('classes', ())
        if len(styles) > 0:
            self.paragraph_style_stack.append(self.rststyle(styles[0]))

    def depart_container(self, node):
        styles = node.attributes.get('classes', ())
        if len(styles) > 0:
            self.paragraph_style_stack.pop()

    def visit_decoration(self, node):
        pass

    def depart_decoration(self, node):
        pass

    def visit_definition_list(self, node):
        self.def_list_level +=1
        if self.list_level > 5:
            raise RuntimeError(
                'max definition list nesting level exceeded')

    def depart_definition_list(self, node):
        self.def_list_level -=1

    def visit_definition_list_item(self, node):
        pass

    def depart_definition_list_item(self, node):
        pass

    def visit_term(self, node):
        el = self.append_p('deflist-term-%d' % self.def_list_level)
        el.text = node.astext()
        self.set_current_element(el)
        raise nodes.SkipChildren()

    def depart_term(self, node):
        self.set_to_parent()

    def visit_definition(self, node):
        self.paragraph_style_stack.append(
            self.rststyle('deflist-def-%d' % self.def_list_level))
        self.bumped_list_level_stack.append(ListLevel(1))

    def depart_definition(self, node):
        self.paragraph_style_stack.pop()
        self.bumped_list_level_stack.pop()

    def visit_classifier(self, node):
        els = self.current_element.getchildren()
        if len(els) > 0:
            el = els[-1]
            el1 = SubElement(el, 'text:span',
                attrib={'text:style-name': self.rststyle('emphasis')
                })
            el1.text = ' (%s)' % (node.astext(), )

    def depart_classifier(self, node):
        pass

    def visit_document(self, node):
        pass

    def depart_document(self, node):
        self.process_footnotes()

    def visit_docinfo(self, node):
        self.section_level += 1
        self.section_count += 1
        if self.settings.create_sections:
            el = self.append_child('text:section', attrib={
                    'text:name': 'Section%d' % self.section_count,
                    'text:style-name': 'Sect%d' % self.section_level,
                    })
            self.set_current_element(el)

    def depart_docinfo(self, node):
        self.section_level -= 1
        if self.settings.create_sections:
            self.set_to_parent()

    def visit_emphasis(self, node):
        el = SubElement(self.current_element, 'text:span',
            attrib={'text:style-name': self.rststyle('emphasis')})
        self.set_current_element(el)

    def depart_emphasis(self, node):
        self.set_to_parent()

    def visit_enumerated_list(self, node):
        el1 = self.current_element
        if self.blockstyle == self.rststyle('blockquote'):
            el2 = SubElement(el1, 'text:list', attrib={
                'text:style-name': self.rststyle('blockquote-enumlist'),
                })
            self.list_style_stack.append(self.rststyle('blockquote-enumitem'))
        elif self.blockstyle == self.rststyle('highlights'):
            el2 = SubElement(el1, 'text:list', attrib={
                'text:style-name': self.rststyle('highlights-enumlist'),
                })
            self.list_style_stack.append(self.rststyle('highlights-enumitem'))
        elif self.blockstyle == self.rststyle('epigraph'):
            el2 = SubElement(el1, 'text:list', attrib={
                'text:style-name': self.rststyle('epigraph-enumlist'),
                })
            self.list_style_stack.append(self.rststyle('epigraph-enumitem'))
        else:
            liststylename = 'enumlist-%s' % (node.get('enumtype', 'arabic'), )
            el2 = SubElement(el1, 'text:list', attrib={
                'text:style-name': self.rststyle(liststylename),
                })
            self.list_style_stack.append(self.rststyle('enumitem'))
        self.set_current_element(el2)

    def depart_enumerated_list(self, node):
        self.set_to_parent()
        self.list_style_stack.pop()

    def visit_list_item(self, node):
        # If we are in a "bumped" list level, then wrap this
        #   list in an outer lists in order to increase the
        #   indentation level.
        if self.in_table_of_contents:
            if self.settings.generate_oowriter_toc:
                self.paragraph_style_stack.append(
                    self.rststyle('contents-%d' % (self.list_level, )))
            else:
                el1 = self.append_child('text:list-item')
                self.set_current_element(el1)
        else:
            el1 = self.append_child('text:list-item')
            el3 = el1
            if len(self.bumped_list_level_stack) > 0:
                level_obj = self.bumped_list_level_stack[-1]
                if level_obj.get_sibling():
                    level_obj.set_nested(False)
                    for level_obj1 in self.bumped_list_level_stack:
                        for idx in range(level_obj1.get_level()):
                            el2 = self.append_child('text:list', parent=el3)
                            el3 = self.append_child(
                                'text:list-item', parent=el2)
            self.paragraph_style_stack.append(self.list_style_stack[-1])
            self.set_current_element(el3)

    def depart_list_item(self, node):
        if self.in_table_of_contents:
            if self.settings.generate_oowriter_toc:
                self.paragraph_style_stack.pop()
            else:
                self.set_to_parent()
        else:
            if len(self.bumped_list_level_stack) > 0:
                level_obj = self.bumped_list_level_stack[-1]
                if level_obj.get_sibling():
                    level_obj.set_nested(True)
                    for level_obj1 in self.bumped_list_level_stack:
                        for idx in range(level_obj1.get_level()):
                            self.set_to_parent()
                            self.set_to_parent()
            self.paragraph_style_stack.pop()
            self.set_to_parent()

    def visit_header(self, node):
        self.in_header = True

    def depart_header(self, node):
        self.in_header = False

    def visit_footer(self, node):
        self.in_footer = True

    def depart_footer(self, node):
        self.in_footer = False

    def visit_field(self, node):
        pass

    def depart_field(self, node):
        pass

    def visit_field_list(self, node):
        pass

    def depart_field_list(self, node):
        pass

    def visit_field_name(self, node):
        el = self.append_p('textbody')
        el1 = SubElement(el, 'text:span',
            attrib={'text:style-name': self.rststyle('strong')})
        el1.text = node.astext()

    def depart_field_name(self, node):
        pass

    def visit_field_body(self, node):
        self.paragraph_style_stack.append(self.rststyle('blockindent'))

    def depart_field_body(self, node):
        self.paragraph_style_stack.pop()

    def visit_figure(self, node):
        pass

    def depart_figure(self, node):
        pass

    def visit_footnote(self, node):
        self.footnote_level += 1
        self.save_footnote_current = self.current_element
        el1 = Element('text:note-body')
        self.current_element = el1
        self.footnote_list.append((node, el1))
        if isinstance(node, docutils.nodes.citation):
            self.paragraph_style_stack.append(self.rststyle('citation'))
        else:
            self.paragraph_style_stack.append(self.rststyle('footnote'))

    def depart_footnote(self, node):
        self.paragraph_style_stack.pop()
        self.current_element = self.save_footnote_current
        self.footnote_level -= 1

    footnote_chars = [
        '*', '**', '***',
        '++', '+++',
        '##', '###',
        '@@', '@@@',
        ]

    def visit_footnote_reference(self, node):
        if self.footnote_level <= 0:
            id = node.attributes['ids'][0]
            refid = node.attributes.get('refid')
            if refid is None:
                refid = ''
            if self.settings.endnotes_end_doc:
                note_class = 'endnote'
            else:
                note_class = 'footnote'
            el1 = self.append_child('text:note', attrib={
                'text:id': '%s' % (refid, ),
                'text:note-class': note_class,
                })
            note_auto = str(node.attributes.get('auto', 1))
            if isinstance(node, docutils.nodes.citation_reference):
                citation = '[%s]' % node.astext()
                el2 = SubElement(el1, 'text:note-citation', attrib={
                    'text:label': citation,
                    })
                el2.text = citation
            elif note_auto == '1':
                el2 = SubElement(el1, 'text:note-citation', attrib={
                    'text:label': node.astext(),
                    })
                el2.text = node.astext()
            elif note_auto == '*':
                if self.footnote_chars_idx >= len(
                    ODFTranslator.footnote_chars):
                    self.footnote_chars_idx = 0
                footnote_char = ODFTranslator.footnote_chars[
                    self.footnote_chars_idx]
                self.footnote_chars_idx += 1
                el2 = SubElement(el1, 'text:note-citation', attrib={
                    'text:label': footnote_char,
                    })
                el2.text = footnote_char
            self.footnote_ref_dict[id] = el1
        raise nodes.SkipChildren()

    def depart_footnote_reference(self, node):
        pass

    def visit_citation(self, node):
        self.in_citation = True
        for id in node.attributes['ids']:
            self.citation_id = id
            break
        self.paragraph_style_stack.append(self.rststyle('blockindent'))
        self.bumped_list_level_stack.append(ListLevel(1))

    def depart_citation(self, node):
        self.citation_id = None
        self.paragraph_style_stack.pop()
        self.bumped_list_level_stack.pop()
        self.in_citation = False

    def visit_citation_reference(self, node):
        if self.settings.create_links:
            id = node.attributes['refid']
            el = self.append_child('text:reference-ref', attrib={
                'text:ref-name': '%s' % (id, ),
                'text:reference-format': 'text',
                })
            el.text = '['
            self.set_current_element(el)
        elif self.current_element.text is None:
            self.current_element.text = '['
        else:
            self.current_element.text += '['

    def depart_citation_reference(self, node):
        self.current_element.text += ']'
        if self.settings.create_links:
            self.set_to_parent()

    def visit_label(self, node):
        if isinstance(node.parent, docutils.nodes.footnote):
            raise nodes.SkipChildren()
        elif self.citation_id is not None:
            el = self.append_p('textbody')
            self.set_current_element(el)
            if self.settings.create_links:
                el0 = SubElement(el, 'text:span')
                el0.text = '['
                el1 = self.append_child('text:reference-mark-start', attrib={
                        'text:name': '%s' % (self.citation_id, ),
                        })
            else:
                el.text = '['

    def depart_label(self, node):
        if isinstance(node.parent, docutils.nodes.footnote):
            pass
        elif self.citation_id is not None:
            if self.settings.create_links:
                el = self.append_child('text:reference-mark-end', attrib={
                        'text:name': '%s' % (self.citation_id, ),
                        })
                el0 = SubElement(self.current_element, 'text:span')
                el0.text = ']'
            else:
                self.current_element.text += ']'
            self.set_to_parent()

    def visit_generated(self, node):
        pass

    def depart_generated(self, node):
        pass

    def check_file_exists(self, path):
        if os.path.exists(path):
            return 1
        else:
            return 0

    def visit_image(self, node):
        # Capture the image file.
        if 'uri' in node.attributes:
            source = node.attributes['uri']
            if not (source.startswith('http:') or source.startswith('https:')):
                if not source.startswith(os.sep):
                    docsource, line = utils.get_source_line(node)
                    if docsource:
                        dirname = os.path.dirname(docsource)
                        if dirname:
                            source = '%s%s%s' % (dirname, os.sep, source, )
                if not self.check_file_exists(source):
                    self.document.reporter.warning(
                        'Cannot find image file %s.' % (source, ))
                    return
        else:
            return
        if source in self.image_dict:
            filename, destination = self.image_dict[source]
        else:
            self.image_count += 1
            filename = os.path.split(source)[1]
            destination = 'Pictures/1%08x%s' % (self.image_count, filename, )
            if source.startswith('http:') or source.startswith('https:'):
                try:
                    imgfile = urllib.request.urlopen(source)
                    content = imgfile.read()
                    imgfile.close()
                    imgfile2 = tempfile.NamedTemporaryFile('wb', delete=False)
                    imgfile2.write(content)
                    imgfile2.close()
                    imgfilename = imgfile2.name
                    source = imgfilename
                except urllib.error.HTTPError as e:
                    self.document.reporter.warning(
                        "Can't open image url %s." % (source, ))
                spec = (source, destination,)
            else:
                spec = (os.path.abspath(source), destination,)
            self.embedded_file_list.append(spec)
            self.image_dict[source] = (source, destination,)
        # Is this a figure (containing an image) or just a plain image?
        if self.in_paragraph:
            el1 = self.current_element
        else:
            el1 = SubElement(self.current_element, 'text:p',
                attrib={'text:style-name': self.rststyle('textbody')})
        el2 = el1
        if isinstance(node.parent, docutils.nodes.figure):
            el3, el4, el5, caption = self.generate_figure(node, source,
                destination, el2)
            attrib = {}
            el6, width = self.generate_image(node, source, destination,
                el5, attrib)
            if caption is not None:
                el6.tail = caption
        else:   #if isinstance(node.parent, docutils.nodes.image):
            el3 = self.generate_image(node, source, destination, el2)

    def depart_image(self, node):
        pass

    def get_image_width_height(self, node, attr):
        size = None
        unit = None
        if attr in node.attributes:
            size = node.attributes[attr]
            size = size.strip()
            # For conversion factors, see:
            # http://www.unitconversion.org/unit_converter/typography-ex.html
            try:
                if size.endswith('%'):
                    if attr == 'height':
                        # Percentage allowed for width but not height.
                        raise ValueError('percentage not allowed for height')
                    size = size.rstrip(' %')
                    size = float(size) / 100.0
                    unit = '%'
                else:
                    size, unit = convert_to_cm(size)
            except ValueError as exp:
                self.document.reporter.warning(
                    'Invalid %s for image: "%s".  '
                    'Error: "%s".' % (
                        attr, node.attributes[attr], exp))
        return size, unit

    def convert_to_cm(self, size):
        """Convert various units to centimeters.

        Note that a call to this method should be wrapped in:
            try: except ValueError:
        """
        size = size.strip()
        if size.endswith('px'):
            size = float(size[:-2]) * 0.026     # convert px to cm
        elif size.endswith('in'):
            size = float(size[:-2]) * 2.54      # convert in to cm
        elif size.endswith('pt'):
            size = float(size[:-2]) * 0.035     # convert pt to cm
        elif size.endswith('pc'):
            size = float(size[:-2]) * 2.371     # convert pc to cm
        elif size.endswith('mm'):
            size = float(size[:-2]) * 10.0      # convert mm to cm
        elif size.endswith('cm'):
            size = float(size[:-2])
        else:
            raise ValueError('unknown unit type')
        unit = 'cm'
        return size, unit

    def get_image_scale(self, node):
        if 'scale' in node.attributes:
            scale = node.attributes['scale']
            try:
                scale = int(scale)
            except ValueError:
                self.document.reporter.warning(
                    'Invalid scale for image: "%s"' % (
                        node.attributes['scale'], ))
            if scale < 1:       # or scale > 100:
                self.document.reporter.warning(
                    'scale out of range (%s), using 1.' % (scale, ))
                scale = 1
            scale = scale * 0.01
        else:
            scale = 1.0
        return scale

    def get_image_scaled_width_height(self, node, source):
        """Return the image size in centimeters adjusted by image attrs."""
        scale = self.get_image_scale(node)
        width, width_unit = self.get_image_width_height(node, 'width')
        height, _ = self.get_image_width_height(node, 'height')
        dpi = (72, 72)
        if PIL is not None and source in self.image_dict:
            filename, destination = self.image_dict[source]
            imageobj = PIL.Image.open(filename, 'r')
            dpi = imageobj.info.get('dpi', dpi)
            # dpi information can be (xdpi, ydpi) or xydpi
            try:
                iter(dpi)
            except:
                dpi = (dpi, dpi)
        else:
            imageobj = None
        if width is None or height is None:
            if imageobj is None:
                raise RuntimeError(
                    'image size not fully specified and PIL not installed')
            if width is None:
                width = imageobj.size[0]
                width = float(width) * 0.026        # convert px to cm
            if height is None:
                height = imageobj.size[1]
                height = float(height) * 0.026      # convert px to cm
            if width_unit == '%':
                factor = width
                image_width = imageobj.size[0]
                image_width = float(image_width) * 0.026    # convert px to cm
                image_height = imageobj.size[1]
                image_height = float(image_height) * 0.026  # convert px to cm
                line_width = self.get_page_width()
                width = factor * line_width
                factor = (factor * line_width) / image_width
                height = factor * image_height
        width *= scale
        height *= scale
        width = '%.2fcm' % width
        height = '%.2fcm' % height
        return width, height

    def get_page_width(self):
        """Return the document's page width in centimeters."""
        root = self.get_dom_stylesheet()
        nodes = root.iterfind(
            './/{urn:oasis:names:tc:opendocument:xmlns:style:1.0}'
            'page-layout/'
            '{urn:oasis:names:tc:opendocument:xmlns:style:1.0}'
            'page-layout-properties')
        width = None
        for node in nodes:
            page_width = node.get(
                '{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}'
                'page-width')
            margin_left = node.get(
                '{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}'
                'margin-left')
            margin_right = node.get(
                '{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}'
                'margin-right')
            if (page_width is None or
                    margin_left is None or
                    margin_right is None):
                continue
            try:
                page_width, _ = self.convert_to_cm(page_width)
                margin_left, _ = self.convert_to_cm(margin_left)
                margin_right, _ = self.convert_to_cm(margin_right)
            except ValueError as exp:
                self.document.reporter.warning(
                    'Stylesheet file contains invalid page width '
                    'or margin size.')
            width = page_width - margin_left - margin_right
        if width is None:
            # We can't find the width in styles, so we make a guess.
            # Use a width of 6 in = 15.24 cm.
            width = 15.24
        return width

    def generate_figure(self, node, source, destination, current_element):
        caption = None
        width, height = self.get_image_scaled_width_height(node, source)
        for node1 in node.parent.children:
            if node1.tagname == 'caption':
                caption = node1.astext()
        self.image_style_count += 1
        #
        # Add the style for the caption.
        if caption is not None:
            attrib = {
                'style:class': 'extra',
                'style:family': 'paragraph',
                'style:name': 'Caption',
                'style:parent-style-name': 'Standard',
                }
            el1 = SubElement(self.automatic_styles, 'style:style',
                attrib=attrib, nsdict=SNSD)
            attrib = {
                'fo:margin-bottom': '0.0835in',
                'fo:margin-top': '0.0835in',
                'text:line-number': '0',
                'text:number-lines': 'false',
                }
            el2 = SubElement(el1, 'style:paragraph-properties', 
                attrib=attrib, nsdict=SNSD)
            attrib = {
                'fo:font-size': '12pt',
                'fo:font-style': 'italic',
                'style:font-name': 'Times',
                'style:font-name-complex': 'Lucidasans1',
                'style:font-size-asian': '12pt',
                'style:font-size-complex': '12pt',
                'style:font-style-asian': 'italic',
                'style:font-style-complex': 'italic',
                }
            el2 = SubElement(el1, 'style:text-properties', 
                attrib=attrib, nsdict=SNSD)
        style_name = 'rstframestyle%d' % self.image_style_count
        draw_name = 'graphics%d' % next(IMAGE_NAME_COUNTER)
        # Add the styles
        attrib = {
            'style:name': style_name,
            'style:family': 'graphic',
            'style:parent-style-name': self.rststyle('figureframe'),
            }
        el1 = SubElement(self.automatic_styles, 
            'style:style', attrib=attrib, nsdict=SNSD)
        halign = 'center'
        valign = 'top'
        if 'align' in node.attributes:
            align = node.attributes['align'].split()
            for val in align:
                if val in ('left', 'center', 'right'):
                    halign = val
                elif val in ('top', 'middle', 'bottom'):
                    valign = val
        attrib = {}
        wrap = False
        classes = node.parent.attributes.get('classes')
        if classes and 'wrap' in classes:
            wrap = True
        if wrap:
            attrib['style:wrap'] = 'dynamic'
        else:
            attrib['style:wrap'] = 'none'
        el2 = SubElement(el1,
            'style:graphic-properties', attrib=attrib, nsdict=SNSD)
        attrib = {
            'draw:style-name': style_name,
            'draw:name': draw_name,
            'text:anchor-type': 'paragraph',
            'draw:z-index': '0',
            }
        attrib['svg:width'] = width
        el3 = SubElement(current_element, 'draw:frame', attrib=attrib)
        attrib = {}
        el4 = SubElement(el3, 'draw:text-box', attrib=attrib)
        attrib = {
            'text:style-name': self.rststyle('caption'),
            }
        el5 = SubElement(el4, 'text:p', attrib=attrib)
        return el3, el4, el5, caption

    def generate_image(self, node, source, destination, current_element,
        frame_attrs=None):
        width, height = self.get_image_scaled_width_height(node, source)
        self.image_style_count += 1
        style_name = 'rstframestyle%d' % self.image_style_count
        # Add the style.
        attrib = {
            'style:name': style_name,
            'style:family': 'graphic',
            'style:parent-style-name': self.rststyle('image'),
            }
        el1 = SubElement(self.automatic_styles, 
            'style:style', attrib=attrib, nsdict=SNSD)
        halign = None
        valign = None
        if 'align' in node.attributes:
            align = node.attributes['align'].split()
            for val in align:
                if val in ('left', 'center', 'right'):
                    halign = val
                elif val in ('top', 'middle', 'bottom'):
                    valign = val
        if frame_attrs is None:
            attrib = {
                'style:vertical-pos': 'top',
                'style:vertical-rel': 'paragraph',
                'style:horizontal-rel': 'paragraph',
                'style:mirror': 'none',
                'fo:clip': 'rect(0cm 0cm 0cm 0cm)',
                'draw:luminance': '0%',
                'draw:contrast': '0%',
                'draw:red': '0%',
                'draw:green': '0%',
                'draw:blue': '0%',
                'draw:gamma': '100%',
                'draw:color-inversion': 'false',
                'draw:image-opacity': '100%',
                'draw:color-mode': 'standard',
                }
        else:
            attrib = frame_attrs
        if halign is not None:
            attrib['style:horizontal-pos'] = halign
        if valign is not None:
            attrib['style:vertical-pos'] = valign
        # If there is a classes/wrap directive or we are 
        #   inside a table, add a no-wrap style.
        wrap = False
        classes = node.attributes.get('classes')
        if classes and 'wrap' in classes:
            wrap = True
        if wrap:
            attrib['style:wrap'] = 'dynamic'
        else:
            attrib['style:wrap'] = 'none'
        # If we are inside a table, add a no-wrap style.
        if self.is_in_table(node):
            attrib['style:wrap'] = 'none'
        el2 = SubElement(el1,
            'style:graphic-properties', attrib=attrib, nsdict=SNSD)
        draw_name = 'graphics%d' % next(IMAGE_NAME_COUNTER)
        # Add the content.
        #el = SubElement(current_element, 'text:p',
        #    attrib={'text:style-name': self.rststyle('textbody')})
        attrib={
            'draw:style-name': style_name,
            'draw:name': draw_name,
            'draw:z-index': '1',
            }
        if isinstance(node.parent, nodes.TextElement):
            attrib['text:anchor-type'] = 'as-char' #vds
        else:
            attrib['text:anchor-type'] = 'paragraph'
        attrib['svg:width'] = width
        attrib['svg:height'] = height
        el1 = SubElement(current_element, 'draw:frame', attrib=attrib)
        el2 = SubElement(el1, 'draw:image', attrib={
            'xlink:href': '%s' % (destination, ),
            'xlink:type': 'simple',
            'xlink:show': 'embed',
            'xlink:actuate': 'onLoad',
            })
        return el1, width

    def is_in_table(self, node):
        node1 = node.parent
        while node1:
            if isinstance(node1, docutils.nodes.entry):
                return True
            node1 = node1.parent
        return False

    def visit_legend(self, node):
        if isinstance(node.parent, docutils.nodes.figure):
            el1 = self.current_element[-1]
            el1 = el1[0][0]
            self.current_element = el1
            self.paragraph_style_stack.append(self.rststyle('legend'))

    def depart_legend(self, node):
        if isinstance(node.parent, docutils.nodes.figure):
            self.paragraph_style_stack.pop()
            self.set_to_parent()
            self.set_to_parent()
            self.set_to_parent()

    def visit_line_block(self, node):
        self.line_indent_level += 1
        self.line_block_level += 1

    def depart_line_block(self, node):
        self.line_indent_level -= 1
        self.line_block_level -= 1

    def visit_line(self, node):
        style = 'lineblock%d' % self.line_indent_level
        el1 = SubElement(self.current_element, 'text:p', attrib={
                'text:style-name': self.rststyle(style),
                })
        self.current_element = el1

    def depart_line(self, node):
        self.set_to_parent()

    def visit_literal(self, node):
        el = SubElement(self.current_element, 'text:span',
            attrib={'text:style-name': self.rststyle('inlineliteral')})
        self.set_current_element(el)

    def depart_literal(self, node):
        self.set_to_parent()

    def visit_inline(self, node):
        styles = node.attributes.get('classes', ())
        if styles:
            el = self.current_element
            for inline_style in styles:
                el = SubElement(el, 'text:span',
                                attrib={'text:style-name':
                                        self.rststyle(inline_style)})
            count = len(styles)
        else:
            # No style was specified so use a default style (old code
            # crashed if no style was given)
            el = SubElement(self.current_element, 'text:span')
            count = 1

        self.set_current_element(el)
        self.inline_style_count_stack.append(count)

    def depart_inline(self, node):
        count = self.inline_style_count_stack.pop()
        for x in range(count):
            self.set_to_parent()

    def _calculate_code_block_padding(self, line):
        count = 0
        matchobj = SPACES_PATTERN.match(line)
        if matchobj:
            pad = matchobj.group()
            count = len(pad)
        else:
            matchobj = TABS_PATTERN.match(line)
            if matchobj:
                pad = matchobj.group()
                count = len(pad) * 8
        return count

    def _add_syntax_highlighting(self, insource, language):
        lexer = pygments.lexers.get_lexer_by_name(language, stripall=True)
        if language in ('latex', 'tex'):
            fmtr = OdtPygmentsLaTeXFormatter(lambda name, parameters=():
                self.rststyle(name, parameters),
                escape_function=escape_cdata)
        else:
            fmtr = OdtPygmentsProgFormatter(lambda name, parameters=():
                self.rststyle(name, parameters),
                escape_function=escape_cdata)
        outsource = pygments.highlight(insource, lexer, fmtr)
        return outsource

    def fill_line(self, line):
        line = FILL_PAT1.sub(self.fill_func1, line)
        line = FILL_PAT2.sub(self.fill_func2, line)
        return line

    def fill_func1(self, matchobj):
        spaces = matchobj.group(0)
        repl = '<text:s text:c="%d"/>' % (len(spaces), )
        return repl

    def fill_func2(self, matchobj):
        spaces = matchobj.group(0)
        repl = ' <text:s text:c="%d"/>' % (len(spaces) - 1, )
        return repl

    def visit_literal_block(self, node):
        if len(self.paragraph_style_stack) > 1:
            wrapper1 = '<text:p text:style-name="%s">%%s</text:p>' % (
                self.rststyle('codeblock-indented'), )
        else:
            wrapper1 = '<text:p text:style-name="%s">%%s</text:p>' % (
                self.rststyle('codeblock'), )
        source = node.astext()
        if (pygments and
            self.settings.add_syntax_highlighting
            #and
            #node.get('hilight', False)
            ):
            language = node.get('language', 'python')
            source = self._add_syntax_highlighting(source, language)
        else:
            source = escape_cdata(source)
        lines = source.split('\n')
        # If there is an empty last line, remove it.
        if lines[-1] == '':
            del lines[-1]
        lines1 = ['<wrappertag1 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">']

        my_lines = []
        for my_line in lines:
            my_line = self.fill_line(my_line)
            my_line = my_line.replace("&#10;", "\n")
            my_lines.append(my_line)
        my_lines_str = '<text:line-break/>'.join(my_lines)
        my_lines_str2 = wrapper1 % (my_lines_str, )
        lines1.append(my_lines_str2)
        lines1.append('</wrappertag1>')
        s1 = ''.join(lines1)
        if WhichElementTree != "lxml":
            s1 = s1.encode("utf-8")
        el1 = etree.fromstring(s1)
        children = el1.getchildren()
        for child in children:
            self.current_element.append(child)

    def depart_literal_block(self, node):
        pass

    visit_doctest_block = visit_literal_block
    depart_doctest_block = depart_literal_block

    # placeholder for math (see docs/dev/todo.txt)
    def visit_math(self, node):
        self.document.reporter.warning('"math" role not supported',
                base_node=node)
        self.visit_literal(node)

    def depart_math(self, node):
        self.depart_literal(node)

    def visit_math_block(self, node):
        self.document.reporter.warning('"math" directive not supported',
                base_node=node)
        self.visit_literal_block(node)

    def depart_math_block(self, node):
        self.depart_literal_block(node)

    def visit_meta(self, node):
        name = node.attributes.get('name')
        content = node.attributes.get('content')
        if name is not None and content is not None:
            self.meta_dict[name] = content

    def depart_meta(self, node):
        pass

    def visit_option_list(self, node):
        table_name = 'tableoption'
        #
        # Generate automatic styles
        if not self.optiontablestyles_generated:
            self.optiontablestyles_generated = True
            el = SubElement(self.automatic_styles, 'style:style', attrib={
                'style:name': self.rststyle(table_name),
                'style:family': 'table'}, nsdict=SNSD)
            el1 = SubElement(el, 'style:table-properties', attrib={
                'style:width': '17.59cm',
                'table:align': 'left',
                'style:shadow': 'none'}, nsdict=SNSD)
            el = SubElement(self.automatic_styles, 'style:style', attrib={
                'style:name': self.rststyle('%s.%%c' % table_name, ( 'A', )),
                'style:family': 'table-column'}, nsdict=SNSD)
            el1 = SubElement(el, 'style:table-column-properties', attrib={
                'style:column-width': '4.999cm'}, nsdict=SNSD)
            el = SubElement(self.automatic_styles, 'style:style', attrib={
                'style:name': self.rststyle('%s.%%c' % table_name, ( 'B', )),
                'style:family': 'table-column'}, nsdict=SNSD)
            el1 = SubElement(el, 'style:table-column-properties', attrib={
                'style:column-width': '12.587cm'}, nsdict=SNSD)
            el = SubElement(self.automatic_styles, 'style:style', attrib={
                'style:name': self.rststyle(
                    '%s.%%c%%d' % table_name, ( 'A', 1, )),
                'style:family': 'table-cell'}, nsdict=SNSD)
            el1 = SubElement(el, 'style:table-cell-properties', attrib={
                'fo:background-color': 'transparent',
                'fo:padding': '0.097cm',
                'fo:border-left': '0.035cm solid #000000',
                'fo:border-right': 'none',
                'fo:border-top': '0.035cm solid #000000',
                'fo:border-bottom': '0.035cm solid #000000'}, nsdict=SNSD)
            el2 = SubElement(el1, 'style:background-image', nsdict=SNSD)
            el = SubElement(self.automatic_styles, 'style:style', attrib={
                'style:name': self.rststyle(
                    '%s.%%c%%d' % table_name, ( 'B', 1, )),
                'style:family': 'table-cell'}, nsdict=SNSD)
            el1 = SubElement(el, 'style:table-cell-properties', attrib={
                'fo:padding': '0.097cm',
                'fo:border': '0.035cm solid #000000'}, nsdict=SNSD)
            el = SubElement(self.automatic_styles, 'style:style', attrib={
                'style:name': self.rststyle(
                    '%s.%%c%%d' % table_name, ( 'A', 2, )),
                'style:family': 'table-cell'}, nsdict=SNSD)
            el1 = SubElement(el, 'style:table-cell-properties', attrib={
                'fo:padding': '0.097cm',
                'fo:border-left': '0.035cm solid #000000',
                'fo:border-right': 'none',
                'fo:border-top': 'none',
                'fo:border-bottom': '0.035cm solid #000000'}, nsdict=SNSD)
            el = SubElement(self.automatic_styles, 'style:style', attrib={
                'style:name': self.rststyle(
                    '%s.%%c%%d' % table_name, ( 'B', 2, )),
                'style:family': 'table-cell'}, nsdict=SNSD)
            el1 = SubElement(el, 'style:table-cell-properties', attrib={
                'fo:padding': '0.097cm',
                'fo:border-left': '0.035cm solid #000000',
                'fo:border-right': '0.035cm solid #000000',
                'fo:border-top': 'none',
                'fo:border-bottom': '0.035cm solid #000000'}, nsdict=SNSD)
        #
        # Generate table data
        el = self.append_child('table:table', attrib={
            'table:name': self.rststyle(table_name),
            'table:style-name': self.rststyle(table_name),
            })
        el1 = SubElement(el, 'table:table-column', attrib={
            'table:style-name': self.rststyle(
                '%s.%%c' % table_name, ( 'A', ))})
        el1 = SubElement(el, 'table:table-column', attrib={
            'table:style-name': self.rststyle(
                '%s.%%c' % table_name, ( 'B', ))})
        el1 = SubElement(el, 'table:table-header-rows')
        el2 = SubElement(el1, 'table:table-row')
        el3 = SubElement(el2, 'table:table-cell', attrib={
            'table:style-name': self.rststyle(
                '%s.%%c%%d' % table_name, ( 'A', 1, )),
            'office:value-type': 'string'})
        el4 = SubElement(el3, 'text:p', attrib={
            'text:style-name': 'Table_20_Heading'})
        el4.text= 'Option'
        el3 = SubElement(el2, 'table:table-cell', attrib={
            'table:style-name': self.rststyle(
                '%s.%%c%%d' % table_name, ( 'B', 1, )),
            'office:value-type': 'string'})
        el4 = SubElement(el3, 'text:p', attrib={
            'text:style-name': 'Table_20_Heading'})
        el4.text= 'Description'
        self.set_current_element(el)

    def depart_option_list(self, node):
        self.set_to_parent()

    def visit_option_list_item(self, node):
        el = self.append_child('table:table-row')
        self.set_current_element(el)

    def depart_option_list_item(self, node):
        self.set_to_parent()

    def visit_option_group(self, node):
        el = self.append_child('table:table-cell', attrib={
            'table:style-name': 'Table%d.A2' % self.table_count,
            'office:value-type': 'string',
        })
        self.set_current_element(el)

    def depart_option_group(self, node):
        self.set_to_parent()

    def visit_option(self, node):
        el = self.append_child('text:p', attrib={
            'text:style-name': 'Table_20_Contents'})
        el.text = node.astext()

    def depart_option(self, node):
        pass

    def visit_option_string(self, node):
        pass

    def depart_option_string(self, node):
        pass

    def visit_option_argument(self, node):
        pass

    def depart_option_argument(self, node):
        pass

    def visit_description(self, node):
        el = self.append_child('table:table-cell', attrib={
            'table:style-name': 'Table%d.B2' % self.table_count,
            'office:value-type': 'string',
        })
        el1 = SubElement(el, 'text:p', attrib={
            'text:style-name': 'Table_20_Contents'})
        el1.text = node.astext()
        raise nodes.SkipChildren()

    def depart_description(self, node):
        pass

    def visit_paragraph(self, node):
        self.in_paragraph = True
        if self.in_header:
            el = self.append_p('header')
        elif self.in_footer:
            el = self.append_p('footer')
        else:
            style_name = self.paragraph_style_stack[-1]
            el = self.append_child('text:p',
                attrib={'text:style-name': style_name})
            self.append_pending_ids(el)
        self.set_current_element(el)

    def depart_paragraph(self, node):
        self.in_paragraph = False
        self.set_to_parent()
        if self.in_header:
            self.header_content.append(
                self.current_element.getchildren()[-1])
            self.current_element.remove(
                self.current_element.getchildren()[-1])
        elif self.in_footer:
            self.footer_content.append(
                self.current_element.getchildren()[-1])
            self.current_element.remove(
                self.current_element.getchildren()[-1])

    def visit_problematic(self, node):
        pass

    def depart_problematic(self, node):
        pass

    def visit_raw(self, node):
        if 'format' in node.attributes:
            formats = node.attributes['format']
            formatlist = formats.split()
            if 'odt' in formatlist:
                rawstr = node.astext()
                attrstr = ' '.join(['%s="%s"' % (k, v, )
                    for k,v in list(CONTENT_NAMESPACE_ATTRIB.items())])
                contentstr = '<stuff %s>%s</stuff>' % (attrstr, rawstr, )
                if WhichElementTree != "lxml":
                    contentstr = contentstr.encode("utf-8")
                content = etree.fromstring(contentstr)
                elements = content.getchildren()
                if len(elements) > 0:
                    el1 = elements[0]
                    if self.in_header:
                        pass
                    elif self.in_footer:
                        pass
                    else:
                        self.current_element.append(el1)
        raise nodes.SkipChildren()

    def depart_raw(self, node):
        if self.in_header:
            pass
        elif self.in_footer:
            pass
        else:
            pass

    def visit_reference(self, node):
        text = node.astext()
        if self.settings.create_links:
            if 'refuri' in node:
                    href = node['refuri']
                    if ( self.settings.cloak_email_addresses
                         and href.startswith('mailto:')):
                        href = self.cloak_mailto(href)
                    el = self.append_child('text:a', attrib={
                        'xlink:href': '%s' % href,
                        'xlink:type': 'simple',
                        })
                    self.set_current_element(el)
            elif 'refid' in node:
                if self.settings.create_links:
                    href = node['refid']
                    el = self.append_child('text:reference-ref', attrib={
                        'text:ref-name': '%s' % href,
                        'text:reference-format': 'text',
                        })
            else:
                self.document.reporter.warning(
                    'References must have "refuri" or "refid" attribute.')
        if (self.in_table_of_contents and
            len(node.children) >= 1 and
            isinstance(node.children[0], docutils.nodes.generated)):
            node.remove(node.children[0])

    def depart_reference(self, node):
        if self.settings.create_links:
            if 'refuri' in node:
                self.set_to_parent()

    def visit_rubric(self, node):
        style_name = self.rststyle('rubric')
        classes = node.get('classes')
        if classes:
            class1 = classes[0]
            if class1:
                style_name = class1
        el = SubElement(self.current_element, 'text:h', attrib = {
            #'text:outline-level': '%d' % section_level,
            #'text:style-name': 'Heading_20_%d' % section_level,
            'text:style-name': style_name,
            })
        text = node.astext()
        el.text = self.encode(text)

    def depart_rubric(self, node):
        pass

    def visit_section(self, node, move_ids=1):
        self.section_level += 1
        self.section_count += 1
        if self.settings.create_sections:
            el = self.append_child('text:section', attrib={
                'text:name': 'Section%d' % self.section_count,
                'text:style-name': 'Sect%d' % self.section_level,
                })
            self.set_current_element(el)

    def depart_section(self, node):
        self.section_level -= 1
        if self.settings.create_sections:
            self.set_to_parent()

    def visit_strong(self, node):
        el = SubElement(self.current_element, 'text:span',
            attrib={'text:style-name': self.rststyle('strong')})
        self.set_current_element(el)

    def depart_strong(self, node):
        self.set_to_parent()

    def visit_substitution_definition(self, node):
        raise nodes.SkipChildren()

    def depart_substitution_definition(self, node):
        pass

    def visit_system_message(self, node):
        pass

    def depart_system_message(self, node):
        pass

    def get_table_style(self, node):
        table_style = None
        table_name = None
        use_predefined_table_style = False
        str_classes = node.get('classes')
        if str_classes is not None:
            for str_class in str_classes:
                if str_class.startswith(TABLESTYLEPREFIX):
                    table_name = str_class
                    use_predefined_table_style = True
                    break
        if table_name is not None:
            table_style = self.table_styles.get(table_name)
            if table_style is None:
                # If we can't find the table style, issue warning
                #   and use the default table style.
                self.document.reporter.warning(
                    'Can\'t find table style "%s".  Using default.' % (
                    table_name, ))
                table_name = TABLENAMEDEFAULT
                table_style = self.table_styles.get(table_name)
                if table_style is None:
                    # If we can't find the default table style, issue a warning
                    #   and use a built-in default style.
                    self.document.reporter.warning(
                        'Can\'t find default table style "%s".  Using built-in default.' % (
                        table_name, ))
                    table_style = BUILTIN_DEFAULT_TABLE_STYLE
        else:
            table_name = TABLENAMEDEFAULT
            table_style = self.table_styles.get(table_name)
            if table_style is None:
                # If we can't find the default table style, issue a warning
                #   and use a built-in default style.
                self.document.reporter.warning(
                    'Can\'t find default table style "%s".  Using built-in default.' % (
                    table_name, ))
                table_style = BUILTIN_DEFAULT_TABLE_STYLE
        return table_style

    def visit_table(self, node):
        self.table_count += 1
        table_style = self.get_table_style(node)
        table_name = '%s%%d' % TABLESTYLEPREFIX
        el1 = SubElement(self.automatic_styles, 'style:style', attrib={
            'style:name': self.rststyle(
                '%s' % table_name, ( self.table_count, )),
            'style:family': 'table',
            }, nsdict=SNSD)
        if table_style.backgroundcolor is None:
            el1_1 = SubElement(el1, 'style:table-properties', attrib={
                #'style:width': '17.59cm',
                #'table:align': 'margins',
                'table:align': 'left',
                'fo:margin-top': '0in',
                'fo:margin-bottom': '0.10in',
                }, nsdict=SNSD)
        else:
            el1_1 = SubElement(el1, 'style:table-properties', attrib={
                #'style:width': '17.59cm',
                'table:align': 'margins',
                'fo:margin-top': '0in',
                'fo:margin-bottom': '0.10in',
                'fo:background-color': table_style.backgroundcolor,
                }, nsdict=SNSD)
        # We use a single cell style for all cells in this table.
        # That's probably not correct, but seems to work.
        el2 = SubElement(self.automatic_styles, 'style:style', attrib={
            'style:name': self.rststyle(
                '%s.%%c%%d' % table_name, ( self.table_count, 'A', 1, )),
            'style:family': 'table-cell',
            }, nsdict=SNSD)
        thickness = self.settings.table_border_thickness
        if thickness is None:
            line_style1 = table_style.border
        else:
            line_style1 = '0.%03dcm solid #000000' % (thickness, )
        el2_1 = SubElement(el2, 'style:table-cell-properties', attrib={
            'fo:padding': '0.049cm',
            'fo:border-left': line_style1,
            'fo:border-right': line_style1,
            'fo:border-top': line_style1,
            'fo:border-bottom': line_style1,
            }, nsdict=SNSD)
        title = None
        for child in node.children:
            if child.tagname == 'title':
                title = child.astext()
                break
        if title is not None:
            el3 = self.append_p('table-title', title)
        else:
            pass
        el4 = SubElement(self.current_element, 'table:table', attrib={
            'table:name': self.rststyle(
                '%s' % table_name, ( self.table_count, )),
            'table:style-name': self.rststyle(
                '%s' % table_name, ( self.table_count, )),
            })
        self.set_current_element(el4)
        self.current_table_style = el1
        self.table_width = 0.0

    def depart_table(self, node):
        attribkey = add_ns('style:width', nsdict=SNSD)
        attribval = '%.4fin' % (self.table_width, )
        el1 = self.current_table_style
        el2 = el1[0]
        el2.attrib[attribkey] = attribval
        self.set_to_parent()

    def visit_tgroup(self, node):
        self.column_count = ord('A') - 1

    def depart_tgroup(self, node):
        pass

    def visit_colspec(self, node):
        self.column_count += 1
        colspec_name = self.rststyle(
            '%s%%d.%%s' % TABLESTYLEPREFIX,
            (self.table_count, chr(self.column_count), )
            )
        colwidth = node['colwidth'] / 12.0
        el1 = SubElement(self.automatic_styles, 'style:style', attrib={
            'style:name': colspec_name,
            'style:family': 'table-column',
            }, nsdict=SNSD)
        el1_1 = SubElement(el1, 'style:table-column-properties', attrib={
            'style:column-width': '%.4fin' % colwidth 
            },
            nsdict=SNSD)
        el2 = self.append_child('table:table-column', attrib={
            'table:style-name': colspec_name,
            })
        self.table_width += colwidth

    def depart_colspec(self, node):
        pass

    def visit_thead(self, node):
        el = self.append_child('table:table-header-rows')
        self.set_current_element(el)
        self.in_thead = True
        self.paragraph_style_stack.append('Table_20_Heading')

    def depart_thead(self, node):
        self.set_to_parent()
        self.in_thead = False
        self.paragraph_style_stack.pop()

    def visit_row(self, node):
        self.column_count = ord('A') - 1
        el = self.append_child('table:table-row')
        self.set_current_element(el)

    def depart_row(self, node):
        self.set_to_parent()

    def visit_entry(self, node):
        self.column_count += 1
        cellspec_name = self.rststyle(
            '%s%%d.%%c%%d' % TABLESTYLEPREFIX, 
            (self.table_count, 'A', 1, )
            )
        attrib={
            'table:style-name': cellspec_name,
            'office:value-type': 'string',
            }
        morecols = node.get('morecols', 0)
        if morecols > 0:
            attrib['table:number-columns-spanned'] = '%d' % (morecols + 1,)
            self.column_count += morecols
        morerows = node.get('morerows', 0)
        if morerows > 0:
            attrib['table:number-rows-spanned'] = '%d' % (morerows + 1,)
        el1 = self.append_child('table:table-cell', attrib=attrib)
        self.set_current_element(el1)

    def depart_entry(self, node):
        self.set_to_parent()

    def visit_tbody(self, node):
        pass

    def depart_tbody(self, node):
        pass

    def visit_target(self, node):
        #
        # I don't know how to implement targets in ODF.
        # How do we create a target in oowriter?  A cross-reference?
        if not ('refuri' in node or 'refid' in node
                or 'refname' in node):
            pass
        else:
            pass

    def depart_target(self, node):
        pass

    def visit_title(self, node, move_ids=1, title_type='title'):
        if isinstance(node.parent, docutils.nodes.section):
            section_level = self.section_level
            if section_level > 7:
                self.document.reporter.warning(
                    'Heading/section levels greater than 7 not supported.')
                self.document.reporter.warning(
                    '    Reducing to heading level 7 for heading: "%s"' % (
                        node.astext(), ))
                section_level = 7
            el1 = self.append_child('text:h', attrib = {
                'text:outline-level': '%d' % section_level,
                #'text:style-name': 'Heading_20_%d' % section_level,
                'text:style-name': self.rststyle(
                    'heading%d', (section_level, )),
                })
            self.append_pending_ids(el1)
            self.set_current_element(el1)
        elif isinstance(node.parent, docutils.nodes.document):
            #    text = self.settings.title
            #else:
            #    text = node.astext()
            el1 = SubElement(self.current_element, 'text:p', attrib = {
                'text:style-name': self.rststyle(title_type),
                })
            self.append_pending_ids(el1)
            text = node.astext()
            self.title = text
            self.found_doc_title = True
            self.set_current_element(el1)

    def depart_title(self, node):
        if (isinstance(node.parent, docutils.nodes.section) or
            isinstance(node.parent, docutils.nodes.document)):
            self.set_to_parent()

    def visit_subtitle(self, node, move_ids=1):
        self.visit_title(node, move_ids, title_type='subtitle')

    def depart_subtitle(self, node):
        self.depart_title(node)

    def visit_title_reference(self, node):
        el = self.append_child('text:span', attrib={
            'text:style-name': self.rststyle('quotation')})
        el.text = self.encode(node.astext())
        raise nodes.SkipChildren()

    def depart_title_reference(self, node):
        pass

    def generate_table_of_content_entry_template(self, el1):
        for idx in range(1, 11):
            el2 = SubElement(el1, 
                'text:table-of-content-entry-template', 
                attrib={
                    'text:outline-level': "%d" % (idx, ),
                    'text:style-name': self.rststyle('contents-%d' % (idx, )),
                })
            el3 = SubElement(el2, 'text:index-entry-chapter')
            el3 = SubElement(el2, 'text:index-entry-text')
            el3 = SubElement(el2, 'text:index-entry-tab-stop', attrib={
                'style:leader-char': ".",
                'style:type': "right",
                })
            el3 = SubElement(el2, 'text:index-entry-page-number')

    def find_title_label(self, node, class_type, label_key):
        label = ''
        title_node = None
        for child in node.children:
            if isinstance(child, class_type):
                title_node = child
                break
        if title_node is not None:
            label = title_node.astext()
        else:
            label = self.language.labels[label_key]
        return label

    def visit_topic(self, node):
        if 'classes' in node.attributes:
            if 'contents' in node.attributes['classes']:
                label = self.find_title_label(node, docutils.nodes.title,
                    'contents')
                if self.settings.generate_oowriter_toc:
                    el1 = self.append_child('text:table-of-content', attrib={
                        'text:name': 'Table of Contents1',
                        'text:protected': 'true',
                        'text:style-name': 'Sect1',
                        })
                    el2 = SubElement(el1,
                        'text:table-of-content-source',
                        attrib={
                            'text:outline-level': '10',
                        })
                    el3 =SubElement(el2, 'text:index-title-template', attrib={
                        'text:style-name': 'Contents_20_Heading',
                        })
                    el3.text = label
                    self.generate_table_of_content_entry_template(el2)
                    el4 = SubElement(el1, 'text:index-body')
                    el5 = SubElement(el4, 'text:index-title')
                    el6 = SubElement(el5, 'text:p', attrib={
                        'text:style-name': self.rststyle('contents-heading'),
                        })
                    el6.text = label
                    self.save_current_element = self.current_element
                    self.table_of_content_index_body = el4
                    self.set_current_element(el4)
                else:
                    el = self.append_p('horizontalline')
                    el = self.append_p('centeredtextbody')
                    el1 = SubElement(el, 'text:span',
                        attrib={'text:style-name': self.rststyle('strong')})
                    el1.text = label
                self.in_table_of_contents = True
            elif 'abstract' in node.attributes['classes']:
                el = self.append_p('horizontalline')
                el = self.append_p('centeredtextbody')
                el1 = SubElement(el, 'text:span',
                    attrib={'text:style-name': self.rststyle('strong')})
                label = self.find_title_label(node, docutils.nodes.title,
                    'abstract')
                el1.text = label
            elif 'dedication' in node.attributes['classes']:
                el = self.append_p('horizontalline')
                el = self.append_p('centeredtextbody')
                el1 = SubElement(el, 'text:span',
                    attrib={'text:style-name': self.rststyle('strong')})
                label = self.find_title_label(node, docutils.nodes.title,
                    'dedication')
                el1.text = label

    def depart_topic(self, node):
        if 'classes' in node.attributes:
            if 'contents' in node.attributes['classes']:
                if self.settings.generate_oowriter_toc:
                    self.update_toc_page_numbers(
                        self.table_of_content_index_body)
                    self.set_current_element(self.save_current_element)
                else:
                    el = self.append_p('horizontalline')
                self.in_table_of_contents = False

    def update_toc_page_numbers(self, el):
        collection = []
        self.update_toc_collect(el, 0, collection)
        self.update_toc_add_numbers(collection)

    def update_toc_collect(self, el, level, collection):
        collection.append((level, el))
        level += 1
        for child_el in el.getchildren():
            if child_el.tag != 'text:index-body':
                self.update_toc_collect(child_el, level, collection)

    def update_toc_add_numbers(self, collection):
        for level, el1 in collection:
            if (el1.tag == 'text:p' and
                el1.text != 'Table of Contents'):
                el2 = SubElement(el1, 'text:tab')
                el2.tail = '9999'


    def visit_transition(self, node):
        el = self.append_p('horizontalline')

    def depart_transition(self, node):
        pass

    #
    # Admonitions
    #
    def visit_warning(self, node):
        self.generate_admonition(node, 'warning')

    def depart_warning(self, node):
        self.paragraph_style_stack.pop()

    def visit_attention(self, node):
        self.generate_admonition(node, 'attention')

    depart_attention = depart_warning

    def visit_caution(self, node):
        self.generate_admonition(node, 'caution')

    depart_caution = depart_warning

    def visit_danger(self, node):
        self.generate_admonition(node, 'danger')

    depart_danger = depart_warning

    def visit_error(self, node):
        self.generate_admonition(node, 'error')

    depart_error = depart_warning

    def visit_hint(self, node):
        self.generate_admonition(node, 'hint')

    depart_hint = depart_warning

    def visit_important(self, node):
        self.generate_admonition(node, 'important')

    depart_important = depart_warning

    def visit_note(self, node):
        self.generate_admonition(node, 'note')

    depart_note = depart_warning

    def visit_tip(self, node):
        self.generate_admonition(node, 'tip')

    depart_tip = depart_warning

    def visit_admonition(self, node):
        title = None
        for child in node.children:
            if child.tagname == 'title':
                title = child.astext()
        if title is None:
            classes1 = node.get('classes')
            if classes1:
                title = classes1[0]
        self.generate_admonition(node, 'generic', title)

    depart_admonition = depart_warning

    def generate_admonition(self, node, label, title=None):
        if hasattr(self.language, 'labels'):
            translated_label = self.language.labels[label]
        else:
            translated_label = label
        el1 = SubElement(self.current_element, 'text:p', attrib={
            'text:style-name': self.rststyle(
                'admon-%s-hdr', (label, )),
        })
        if title:
            el1.text = title
        else:
            el1.text = '%s!' % (translated_label.capitalize(), )
        s1 = self.rststyle('admon-%s-body', (label, ))
        self.paragraph_style_stack.append(s1)

    #
    # Roles (e.g. subscript, superscript, strong, ...
    #
    def visit_subscript(self, node):
        el = self.append_child('text:span', attrib={
            'text:style-name': 'rststyle-subscript',
            })
        self.set_current_element(el)

    def depart_subscript(self, node):
        self.set_to_parent()

    def visit_superscript(self, node):
        el = self.append_child('text:span', attrib={
            'text:style-name': 'rststyle-superscript',
            })
        self.set_current_element(el)

    def depart_superscript(self, node):
        self.set_to_parent()


# Use an own reader to modify transformations done.
class Reader(standalone.Reader):

    def get_transforms(self):
        default = standalone.Reader.get_transforms(self)
        if self.settings.create_links:
            return default
        return [ i
                 for i in default
                 if i is not references.DanglingReferences ]
