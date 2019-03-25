# $Id: core.py 8126 2017-06-23 09:34:28Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Calling the ``publish_*`` convenience functions (or instantiating a
`Publisher` object) with component names will result in default
behavior.  For custom behavior (setting component options), create
custom component objects first, and pass *them* to
``publish_*``/`Publisher`.  See `The Docutils Publisher`_.

.. _The Docutils Publisher: http://docutils.sf.net/docs/api/publisher.html
"""

__docformat__ = 'reStructuredText'

import sys
import pprint
from docutils import __version__, __version_details__, SettingsSpec
from docutils import frontend, io, utils, readers, writers
from docutils.frontend import OptionParser
from docutils.transforms import Transformer
from docutils.utils.error_reporting import ErrorOutput, ErrorString
import docutils.readers.doctree

class Publisher:

    """
    A facade encapsulating the high-level logic of a Docutils system.
    """

    def __init__(self, reader=None, parser=None, writer=None,
                 source=None, source_class=io.FileInput,
                 destination=None, destination_class=io.FileOutput,
                 settings=None):
        """
        Initial setup.  If any of `reader`, `parser`, or `writer` are not
        specified, the corresponding ``set_...`` method should be called with
        a component name (`set_reader` sets the parser as well).
        """

        self.document = None
        """The document tree (`docutils.nodes` objects)."""

        self.reader = reader
        """A `docutils.readers.Reader` instance."""

        self.parser = parser
        """A `docutils.parsers.Parser` instance."""

        self.writer = writer
        """A `docutils.writers.Writer` instance."""

        for component in 'reader', 'parser', 'writer':
            assert not isinstance(getattr(self, component), str), (
                'passed string "%s" as "%s" parameter; pass an instance, '
                'or use the "%s_name" parameter instead (in '
                'docutils.core.publish_* convenience functions).'
                % (getattr(self, component), component, component))

        self.source = source
        """The source of input data, a `docutils.io.Input` instance."""

        self.source_class = source_class
        """The class for dynamically created source objects."""

        self.destination = destination
        """The destination for docutils output, a `docutils.io.Output`
        instance."""

        self.destination_class = destination_class
        """The class for dynamically created destination objects."""

        self.settings = settings
        """An object containing Docutils settings as instance attributes.
        Set by `self.process_command_line()` or `self.get_settings()`."""

        self._stderr = ErrorOutput()

    def set_reader(self, reader_name, parser, parser_name):
        """Set `self.reader` by name."""
        reader_class = readers.get_reader_class(reader_name)
        self.reader = reader_class(parser, parser_name)
        self.parser = self.reader.parser

    def set_writer(self, writer_name):
        """Set `self.writer` by name."""
        writer_class = writers.get_writer_class(writer_name)
        self.writer = writer_class()

    def set_components(self, reader_name, parser_name, writer_name):
        if self.reader is None:
            self.set_reader(reader_name, self.parser, parser_name)
        if self.parser is None:
            if self.reader.parser is None:
                self.reader.set_parser(parser_name)
            self.parser = self.reader.parser
        if self.writer is None:
            self.set_writer(writer_name)

    def setup_option_parser(self, usage=None, description=None,
                            settings_spec=None, config_section=None,
                            **defaults):
        if config_section:
            if not settings_spec:
                settings_spec = SettingsSpec()
            settings_spec.config_section = config_section
            parts = config_section.split()
            if len(parts) > 1 and parts[-1] == 'application':
                settings_spec.config_section_dependencies = ['applications']
        #@@@ Add self.source & self.destination to components in future?
        option_parser = OptionParser(
            components=(self.parser, self.reader, self.writer, settings_spec),
            defaults=defaults, read_config_files=True,
            usage=usage, description=description)
        return option_parser

    def get_settings(self, usage=None, description=None,
                     settings_spec=None, config_section=None, **defaults):
        """
        Set and return default settings (overrides in `defaults` dict).

        Set components first (`self.set_reader` & `self.set_writer`).
        Explicitly setting `self.settings` disables command line option
        processing from `self.publish()`.
        """
        option_parser = self.setup_option_parser(
            usage, description, settings_spec, config_section, **defaults)
        self.settings = option_parser.get_default_values()
        return self.settings

    def process_programmatic_settings(self, settings_spec,
                                      settings_overrides,
                                      config_section):
        if self.settings is None:
            defaults = (settings_overrides or {}).copy()
            # Propagate exceptions by default when used programmatically:
            defaults.setdefault('traceback', True)
            self.get_settings(settings_spec=settings_spec,
                              config_section=config_section,
                              **defaults)

    def process_command_line(self, argv=None, usage=None, description=None,
                             settings_spec=None, config_section=None,
                             **defaults):
        """
        Pass an empty list to `argv` to avoid reading `sys.argv` (the
        default).

        Set components first (`self.set_reader` & `self.set_writer`).
        """
        option_parser = self.setup_option_parser(
            usage, description, settings_spec, config_section, **defaults)
        if argv is None:
            argv = sys.argv[1:]
            # converting to Unicode (Python 3 does this automatically):
            if sys.version_info < (3,0):
                # TODO: make this failsafe and reversible?
                argv_encoding = (frontend.locale_encoding or 'ascii')
                argv = [a.decode(argv_encoding) for a in argv]
        self.settings = option_parser.parse_args(argv)

    def set_io(self, source_path=None, destination_path=None):
        if self.source is None:
            self.set_source(source_path=source_path)
        if self.destination is None:
            self.set_destination(destination_path=destination_path)

    def set_source(self, source=None, source_path=None):
        if source_path is None:
            source_path = self.settings._source
        else:
            self.settings._source = source_path
        # Raise IOError instead of system exit with `tracback == True`
        # TODO: change io.FileInput's default behaviour and remove this hack
        try:
            self.source = self.source_class(
                source=source, source_path=source_path,
                encoding=self.settings.input_encoding)
        except TypeError:
            self.source = self.source_class(
                source=source, source_path=source_path,
                encoding=self.settings.input_encoding)

    def set_destination(self, destination=None, destination_path=None):
        if destination_path is None:
            destination_path = self.settings._destination
        else:
            self.settings._destination = destination_path
        self.destination = self.destination_class(
            destination=destination, destination_path=destination_path,
            encoding=self.settings.output_encoding,
            error_handler=self.settings.output_encoding_error_handler)

    def apply_transforms(self):
        self.document.transformer.populate_from_components(
            (self.source, self.reader, self.reader.parser, self.writer,
             self.destination))
        self.document.transformer.apply_transforms()

    def publish(self, argv=None, usage=None, description=None,
                settings_spec=None, settings_overrides=None,
                config_section=None, enable_exit_status=False):
        """
        Process command line options and arguments (if `self.settings` not
        already set), run `self.reader` and then `self.writer`.  Return
        `self.writer`'s output.
        """
        exit = None
        try:
            if self.settings is None:
                self.process_command_line(
                    argv, usage, description, settings_spec, config_section,
                    **(settings_overrides or {}))
            self.set_io()
            self.document = self.reader.read(self.source, self.parser,
                                             self.settings)
            self.apply_transforms()
            output = self.writer.write(self.document, self.destination)
            self.writer.assemble_parts()
        except SystemExit as error:
            exit = 1
            exit_status = error.code
        except Exception as error:
            if not self.settings:       # exception too early to report nicely
                raise
            if self.settings.traceback: # Propagate exceptions?
                self.debugging_dumps()
                raise
            self.report_Exception(error)
            exit = True
            exit_status = 1
        self.debugging_dumps()
        if (enable_exit_status and self.document
            and (self.document.reporter.max_level
                 >= self.settings.exit_status_level)):
            sys.exit(self.document.reporter.max_level + 10)
        elif exit:
            sys.exit(exit_status)
        return output

    def debugging_dumps(self):
        if not self.document:
            return
        if self.settings.dump_settings:
            print('\n::: Runtime settings:', file=self._stderr)
            print(pprint.pformat(self.settings.__dict__), file=self._stderr)
        if self.settings.dump_internals:
            print('\n::: Document internals:', file=self._stderr)
            print(pprint.pformat(self.document.__dict__), file=self._stderr)
        if self.settings.dump_transforms:
            print('\n::: Transforms applied:', file=self._stderr)
            print((' (priority, transform class, '
                                 'pending node details, keyword args)'), file=self._stderr)
            print(pprint.pformat(
                [(priority, '%s.%s' % (xclass.__module__, xclass.__name__),
                  pending and pending.details, kwargs)
                 for priority, xclass, pending, kwargs
                 in self.document.transformer.applied]), file=self._stderr)
        if self.settings.dump_pseudo_xml:
            print('\n::: Pseudo-XML:', file=self._stderr)
            print(self.document.pformat().encode(
                'raw_unicode_escape'), file=self._stderr)

    def report_Exception(self, error):
        if isinstance(error, utils.SystemMessage):
            self.report_SystemMessage(error)
        elif isinstance(error, UnicodeEncodeError):
            self.report_UnicodeError(error)
        elif isinstance(error, io.InputError):
            self._stderr.write('Unable to open source file for reading:\n'
                               '  %s\n' % ErrorString(error))
        elif isinstance(error, io.OutputError):
            self._stderr.write(
                'Unable to open destination file for writing:\n'
                '  %s\n' % ErrorString(error))
        else:
            print('%s' % ErrorString(error), file=self._stderr)
            print(("""\
Exiting due to error.  Use "--traceback" to diagnose.
Please report errors to <docutils-users@lists.sf.net>.
Include "--traceback" output, Docutils version (%s%s),
Python version (%s), your OS type & version, and the
command line used.""" % (__version__,
                         docutils.__version_details__ and
                         ' [%s]'%docutils.__version_details__ or '',
                         sys.version.split()[0])), file=self._stderr)

    def report_SystemMessage(self, error):
        print(('Exiting due to level-%s (%s) system message.'
                             % (error.level,
                                utils.Reporter.levels[error.level])), file=self._stderr)

    def report_UnicodeError(self, error):
        data = error.object[error.start:error.end]
        self._stderr.write(
            '%s\n'
            '\n'
            'The specified output encoding (%s) cannot\n'
            'handle all of the output.\n'
            'Try setting "--output-encoding-error-handler" to\n'
            '\n'
            '* "xmlcharrefreplace" (for HTML & XML output);\n'
            '  the output will contain "%s" and should be usable.\n'
            '* "backslashreplace" (for other output formats);\n'
            '  look for "%s" in the output.\n'
            '* "replace"; look for "?" in the output.\n'
            '\n'
            '"--output-encoding-error-handler" is currently set to "%s".\n'
            '\n'
            'Exiting due to error.  Use "--traceback" to diagnose.\n'
            'If the advice above doesn\'t eliminate the error,\n'
            'please report it to <docutils-users@lists.sf.net>.\n'
            'Include "--traceback" output, Docutils version (%s),\n'
            'Python version (%s), your OS type & version, and the\n'
            'command line used.\n'
            % (ErrorString(error),
               self.settings.output_encoding,
               data.encode('ascii', 'xmlcharrefreplace'),
               data.encode('ascii', 'backslashreplace'),
               self.settings.output_encoding_error_handler,
               __version__, sys.version.split()[0]))

default_usage = '%prog [options] [<source> [<destination>]]'
default_description = ('Reads from <source> (default is stdin) and writes to '
                       '<destination> (default is stdout).  See '
                       '<http://docutils.sf.net/docs/user/config.html> for '
                       'the full reference.')

def publish_cmdline(reader=None, reader_name='standalone',
                    parser=None, parser_name='restructuredtext',
                    writer=None, writer_name='pseudoxml',
                    settings=None, settings_spec=None,
                    settings_overrides=None, config_section=None,
                    enable_exit_status=True, argv=None,
                    usage=default_usage, description=default_description):
    """
    Set up & run a `Publisher` for command-line-based file I/O (input and
    output file paths taken automatically from the command line).  Return the
    encoded string output also.

    Parameters: see `publish_programmatically` for the remainder.

    - `argv`: Command-line argument list to use instead of ``sys.argv[1:]``.
    - `usage`: Usage string, output if there's a problem parsing the command
      line.
    - `description`: Program description, output for the "--help" option
      (along with command-line option descriptions).
    """
    pub = Publisher(reader, parser, writer, settings=settings)
    pub.set_components(reader_name, parser_name, writer_name)
    output = pub.publish(
        argv, usage, description, settings_spec, settings_overrides,
        config_section=config_section, enable_exit_status=enable_exit_status)
    return output

def publish_file(source=None, source_path=None,
                 destination=None, destination_path=None,
                 reader=None, reader_name='standalone',
                 parser=None, parser_name='restructuredtext',
                 writer=None, writer_name='pseudoxml',
                 settings=None, settings_spec=None, settings_overrides=None,
                 config_section=None, enable_exit_status=False):
    """
    Set up & run a `Publisher` for programmatic use with file-like I/O.
    Return the encoded string output also.

    Parameters: see `publish_programmatically`.
    """
    output, pub = publish_programmatically(
        source_class=io.FileInput, source=source, source_path=source_path,
        destination_class=io.FileOutput,
        destination=destination, destination_path=destination_path,
        reader=reader, reader_name=reader_name,
        parser=parser, parser_name=parser_name,
        writer=writer, writer_name=writer_name,
        settings=settings, settings_spec=settings_spec,
        settings_overrides=settings_overrides,
        config_section=config_section,
        enable_exit_status=enable_exit_status)
    return output

def publish_string(source, source_path=None, destination_path=None,
                   reader=None, reader_name='standalone',
                   parser=None, parser_name='restructuredtext',
                   writer=None, writer_name='pseudoxml',
                   settings=None, settings_spec=None,
                   settings_overrides=None, config_section=None,
                   enable_exit_status=False):
    """
    Set up & run a `Publisher` for programmatic use with string I/O.  Return
    the encoded string or Unicode string output.

    For encoded string output, be sure to set the 'output_encoding' setting to
    the desired encoding.  Set it to 'unicode' for unencoded Unicode string
    output.  Here's one way::

        publish_string(..., settings_overrides={'output_encoding': 'unicode'})

    Similarly for Unicode string input (`source`)::

        publish_string(..., settings_overrides={'input_encoding': 'unicode'})

    Parameters: see `publish_programmatically`.
    """
    output, pub = publish_programmatically(
        source_class=io.StringInput, source=source, source_path=source_path,
        destination_class=io.StringOutput,
        destination=None, destination_path=destination_path,
        reader=reader, reader_name=reader_name,
        parser=parser, parser_name=parser_name,
        writer=writer, writer_name=writer_name,
        settings=settings, settings_spec=settings_spec,
        settings_overrides=settings_overrides,
        config_section=config_section,
        enable_exit_status=enable_exit_status)
    return output

def publish_parts(source, source_path=None, source_class=io.StringInput,
                  destination_path=None,
                  reader=None, reader_name='standalone',
                  parser=None, parser_name='restructuredtext',
                  writer=None, writer_name='pseudoxml',
                  settings=None, settings_spec=None,
                  settings_overrides=None, config_section=None,
                  enable_exit_status=False):
    """
    Set up & run a `Publisher`, and return a dictionary of document parts.
    Dictionary keys are the names of parts, and values are Unicode strings;
    encoding is up to the client.  For programmatic use with string I/O.

    For encoded string input, be sure to set the 'input_encoding' setting to
    the desired encoding.  Set it to 'unicode' for unencoded Unicode string
    input.  Here's how::

        publish_parts(..., settings_overrides={'input_encoding': 'unicode'})

    Parameters: see `publish_programmatically`.
    """
    output, pub = publish_programmatically(
        source=source, source_path=source_path, source_class=source_class,
        destination_class=io.StringOutput,
        destination=None, destination_path=destination_path,
        reader=reader, reader_name=reader_name,
        parser=parser, parser_name=parser_name,
        writer=writer, writer_name=writer_name,
        settings=settings, settings_spec=settings_spec,
        settings_overrides=settings_overrides,
        config_section=config_section,
        enable_exit_status=enable_exit_status)
    return pub.writer.parts

def publish_doctree(source, source_path=None,
                    source_class=io.StringInput,
                    reader=None, reader_name='standalone',
                    parser=None, parser_name='restructuredtext',
                    settings=None, settings_spec=None,
                    settings_overrides=None, config_section=None,
                    enable_exit_status=False):
    """
    Set up & run a `Publisher` for programmatic use with string I/O.
    Return the document tree.

    For encoded string input, be sure to set the 'input_encoding' setting to
    the desired encoding.  Set it to 'unicode' for unencoded Unicode string
    input.  Here's one way::

        publish_doctree(..., settings_overrides={'input_encoding': 'unicode'})

    Parameters: see `publish_programmatically`.
    """
    pub = Publisher(reader=reader, parser=parser, writer=None,
                    settings=settings,
                    source_class=source_class,
                    destination_class=io.NullOutput)
    pub.set_components(reader_name, parser_name, 'null')
    pub.process_programmatic_settings(
        settings_spec, settings_overrides, config_section)
    pub.set_source(source, source_path)
    pub.set_destination(None, None)
    output = pub.publish(enable_exit_status=enable_exit_status)
    return pub.document

def publish_from_doctree(document, destination_path=None,
                         writer=None, writer_name='pseudoxml',
                         settings=None, settings_spec=None,
                         settings_overrides=None, config_section=None,
                         enable_exit_status=False):
    """
    Set up & run a `Publisher` to render from an existing document
    tree data structure, for programmatic use with string I/O.  Return
    the encoded string output.

    Note that document.settings is overridden; if you want to use the settings
    of the original `document`, pass settings=document.settings.

    Also, new document.transformer and document.reporter objects are
    generated.

    For encoded string output, be sure to set the 'output_encoding' setting to
    the desired encoding.  Set it to 'unicode' for unencoded Unicode string
    output.  Here's one way::

        publish_from_doctree(
            ..., settings_overrides={'output_encoding': 'unicode'})

    Parameters: `document` is a `docutils.nodes.document` object, an existing
    document tree.

    Other parameters: see `publish_programmatically`.
    """
    reader = docutils.readers.doctree.Reader(parser_name='null')
    pub = Publisher(reader, None, writer,
                    source=io.DocTreeInput(document),
                    destination_class=io.StringOutput, settings=settings)
    if not writer and writer_name:
        pub.set_writer(writer_name)
    pub.process_programmatic_settings(
        settings_spec, settings_overrides, config_section)
    pub.set_destination(None, destination_path)
    return pub.publish(enable_exit_status=enable_exit_status)

def publish_cmdline_to_binary(reader=None, reader_name='standalone',
                    parser=None, parser_name='restructuredtext',
                    writer=None, writer_name='pseudoxml',
                    settings=None, settings_spec=None,
                    settings_overrides=None, config_section=None,
                    enable_exit_status=True, argv=None,
                    usage=default_usage, description=default_description,
                    destination=None, destination_class=io.BinaryFileOutput
                    ):
    """
    Set up & run a `Publisher` for command-line-based file I/O (input and
    output file paths taken automatically from the command line).  Return the
    encoded string output also.

    This is just like publish_cmdline, except that it uses
    io.BinaryFileOutput instead of io.FileOutput.

    Parameters: see `publish_programmatically` for the remainder.

    - `argv`: Command-line argument list to use instead of ``sys.argv[1:]``.
    - `usage`: Usage string, output if there's a problem parsing the command
      line.
    - `description`: Program description, output for the "--help" option
      (along with command-line option descriptions).
    """
    pub = Publisher(reader, parser, writer, settings=settings,
        destination_class=destination_class)
    pub.set_components(reader_name, parser_name, writer_name)
    output = pub.publish(
        argv, usage, description, settings_spec, settings_overrides,
        config_section=config_section, enable_exit_status=enable_exit_status)
    return output

def publish_programmatically(source_class, source, source_path,
                             destination_class, destination, destination_path,
                             reader, reader_name,
                             parser, parser_name,
                             writer, writer_name,
                             settings, settings_spec,
                             settings_overrides, config_section,
                             enable_exit_status):
    """
    Set up & run a `Publisher` for custom programmatic use.  Return the
    encoded string output and the Publisher object.

    Applications should not need to call this function directly.  If it does
    seem to be necessary to call this function directly, please write to the
    Docutils-develop mailing list
    <http://docutils.sf.net/docs/user/mailing-lists.html#docutils-develop>.

    Parameters:

    * `source_class` **required**: The class for dynamically created source
      objects.  Typically `io.FileInput` or `io.StringInput`.

    * `source`: Type depends on `source_class`:

      - If `source_class` is `io.FileInput`: Either a file-like object
        (must have 'read' and 'close' methods), or ``None``
        (`source_path` is opened).  If neither `source` nor
        `source_path` are supplied, `sys.stdin` is used.

      - If `source_class` is `io.StringInput` **required**: The input
        string, either an encoded 8-bit string (set the
        'input_encoding' setting to the correct encoding) or a Unicode
        string (set the 'input_encoding' setting to 'unicode').

    * `source_path`: Type depends on `source_class`:

      - `io.FileInput`: Path to the input file, opened if no `source`
        supplied.

      - `io.StringInput`: Optional.  Path to the file or object that produced
        `source`.  Only used for diagnostic output.

    * `destination_class` **required**: The class for dynamically created
      destination objects.  Typically `io.FileOutput` or `io.StringOutput`.

    * `destination`: Type depends on `destination_class`:

      - `io.FileOutput`: Either a file-like object (must have 'write' and
        'close' methods), or ``None`` (`destination_path` is opened).  If
        neither `destination` nor `destination_path` are supplied,
        `sys.stdout` is used.

      - `io.StringOutput`: Not used; pass ``None``.

    * `destination_path`: Type depends on `destination_class`:

      - `io.FileOutput`: Path to the output file.  Opened if no `destination`
        supplied.

      - `io.StringOutput`: Path to the file or object which will receive the
        output; optional.  Used for determining relative paths (stylesheets,
        source links, etc.).

    * `reader`: A `docutils.readers.Reader` object.

    * `reader_name`: Name or alias of the Reader class to be instantiated if
      no `reader` supplied.

    * `parser`: A `docutils.parsers.Parser` object.

    * `parser_name`: Name or alias of the Parser class to be instantiated if
      no `parser` supplied.

    * `writer`: A `docutils.writers.Writer` object.

    * `writer_name`: Name or alias of the Writer class to be instantiated if
      no `writer` supplied.

    * `settings`: A runtime settings (`docutils.frontend.Values`) object, for
      dotted-attribute access to runtime settings.  It's the end result of the
      `SettingsSpec`, config file, and option processing.  If `settings` is
      passed, it's assumed to be complete and no further setting/config/option
      processing is done.

    * `settings_spec`: A `docutils.SettingsSpec` subclass or object.  Provides
      extra application-specific settings definitions independently of
      components.  In other words, the application becomes a component, and
      its settings data is processed along with that of the other components.
      Used only if no `settings` specified.

    * `settings_overrides`: A dictionary containing application-specific
      settings defaults that override the defaults of other components.
      Used only if no `settings` specified.

    * `config_section`: A string, the name of the configuration file section
      for this application.  Overrides the ``config_section`` attribute
      defined by `settings_spec`.  Used only if no `settings` specified.

    * `enable_exit_status`: Boolean; enable exit status at end of processing?
    """
    pub = Publisher(reader, parser, writer, settings=settings,
                    source_class=source_class,
                    destination_class=destination_class)
    pub.set_components(reader_name, parser_name, writer_name)
    pub.process_programmatic_settings(
        settings_spec, settings_overrides, config_section)
    pub.set_source(source, source_path)
    pub.set_destination(destination, destination_path)
    output = pub.publish(enable_exit_status=enable_exit_status)
    return output, pub
