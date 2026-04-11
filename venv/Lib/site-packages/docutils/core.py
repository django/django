# $Id: core.py 10267 2025-12-01 22:43:32Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Calling the ``publish_*`` convenience functions (or instantiating a
`Publisher` object) with component names will result in default
behavior.  For custom behavior (setting component options), create
custom component objects first, and pass *them* to
``publish_*``/`Publisher`.  See `The Docutils Publisher`_.

.. _The Docutils Publisher:
    https://docutils.sourceforge.io/docs/api/publisher.html
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

import locale
import pprint
import os
import sys
import warnings

from docutils import (__version__, __version_details__, SettingsSpec,
                      io, utils, readers, parsers, writers)
from docutils.frontend import OptionParser
from docutils.readers import doctree

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import TextIO
    from docutils.nodes import StrPath


class Publisher:

    """
    A facade encapsulating the high-level logic of a Docutils system.
    """

    def __init__(self, reader=None, parser=None, writer=None,
                 source=None, source_class=io.FileInput,
                 destination=None, destination_class=io.FileOutput,
                 settings=None) -> None:
        """
        Initial setup.

        The components `reader`, `parser`, or `writer` should all be
        specified, either as instances or via their names.
        """
        # get component instances from their names:
        if isinstance(reader, str):
            reader = readers.get_reader_class(reader)(parser)
        if isinstance(parser, str):
            if isinstance(reader, readers.Reader):
                if reader.parser is None:
                    reader.set_parser(parser)
                parser = reader.parser
            else:
                parser = parsers.get_parser_class(parser)()
        if isinstance(writer, str):
            writer = writers.get_writer_class(writer)()

        self.document = None
        """The document tree (`docutils.nodes` objects)."""

        self.reader = reader
        """A `docutils.readers.Reader` instance."""

        self.parser = parser
        """A `docutils.parsers.Parser` instance."""

        self.writer = writer
        """A `docutils.writers.Writer` instance."""

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

        self._stderr = io.ErrorOutput()

    def set_reader(self, reader, parser=None, parser_name=None) -> None:
        """Set `self.reader` by name.

        The "paser_name" argument is deprecated,
        use "parser" with parser name or instance.
        """
        reader_class = readers.get_reader_class(reader)
        self.reader = reader_class(parser, parser_name)
        if self.reader.parser is not None:
            self.parser = self.reader.parser
        elif self.parser is not None:
            self.reader.parser = self.parser

    def set_writer(self, writer_name) -> None:
        """Set `self.writer` by name."""
        writer_class = writers.get_writer_class(writer_name)
        self.writer = writer_class()

    def set_components(self, reader_name, parser_name, writer_name) -> None:
        warnings.warn('`Publisher.set_components()` will be removed in '
                      'Docutils 2.0.  Specify component names '
                      'at instantiation.',
                      PendingDeprecationWarning, stacklevel=2)
        if self.reader is None:
            self.set_reader(reader_name, self.parser, parser_name)
        if self.parser is None:
            if self.reader.parser is None:
                self.reader.set_parser(parser_name)
            self.parser = self.reader.parser
        if self.writer is None:
            self.set_writer(writer_name)

    def _setup_settings_parser(self, usage=None, description=None,
                               settings_spec=None, config_section=None,
                               **defaults):
        # Provisional: will change (docutils.frontend.OptionParser will
        # be replaced by a parser based on arparse.ArgumentParser)
        # and may be removed later.
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            if config_section:
                if not settings_spec:
                    settings_spec = SettingsSpec()
                settings_spec.config_section = config_section
                parts = config_section.split()
                if len(parts) > 1 and parts[-1] == 'application':
                    settings_spec.config_section_dependencies = ['applications']  # noqa: E501
            # @@@ Add self.source & self.destination to components in future?
            return OptionParser(
                components=(self.parser, self.reader, self.writer,
                            settings_spec),
                defaults=defaults, read_config_files=True,
                usage=usage, description=description)

    def get_settings(self, usage=None, description=None,
                     settings_spec=None, config_section=None, **defaults):
        """
        Return settings from components and config files.

        Please set components first (`self.set_reader` & `self.set_writer`).
        Use keyword arguments to override component defaults
        (before updating from configuration files).

        Calling this function also sets `self.settings` which makes
        `self.publish()` skip parsing command line options.
        """
        option_parser = self._setup_settings_parser(
            usage, description, settings_spec, config_section, **defaults)
        self.settings = option_parser.get_default_values()
        return self.settings

    def process_programmatic_settings(self, settings_spec,
                                      settings_overrides,
                                      config_section) -> None:
        if self.settings is None:
            defaults = settings_overrides.copy() if settings_overrides else {}
            # Propagate exceptions by default when used programmatically:
            defaults.setdefault('traceback', True)
            self.get_settings(settings_spec=settings_spec,
                              config_section=config_section,
                              **defaults)

    def process_command_line(self, argv=None, usage=None, description=None,
                             settings_spec=None, config_section=None,
                             **defaults) -> None:
        """
        Parse command line arguments and set ``self.settings``.

        Pass an empty sequence to `argv` to avoid reading `sys.argv`
        (the default behaviour).

        Set components first (`self.set_reader` & `self.set_writer`).
        """
        option_parser = self._setup_settings_parser(
            usage, description, settings_spec, config_section, **defaults)
        if argv is None:
            argv = sys.argv[1:]
        self.settings = option_parser.parse_args(argv)

    def set_io(self, source_path=None, destination_path=None) -> None:
        if self.source is None:
            self.set_source(source_path=source_path)
        if self.destination is None:
            self.set_destination(destination_path=destination_path)

    def set_source(self,
                   source: str | None = None,
                   source_path: StrPath | None = None,
                   ) -> None:
        if source_path is None:
            source_path = self.settings._source
        else:
            source_path = os.fspath(source_path)
            self.settings._source = source_path
        self.source = self.source_class(
            source=source, source_path=source_path,
            encoding=self.settings.input_encoding,
            error_handler=self.settings.input_encoding_error_handler)

    def set_destination(self,
                        destination: TextIO | None = None,
                        destination_path: StrPath | None = None,
                        ) -> None:
        # Provisional: the "_destination" and "output" settings
        # are deprecated and will be ignored in Docutils 2.0.
        if destination_path is not None:
            self.settings.output_path = os.fspath(destination_path)
        else:
            # check 'output_path' and legacy settings
            if getattr(self.settings, 'output', None
                       ) and not self.settings.output_path:
                self.settings.output_path = self.settings.output
            if (self.settings.output_path and self.settings._destination
                and self.settings.output_path != self.settings._destination):
                raise SystemExit('The --output-path option obsoletes the '
                                 'second positional argument (DESTINATION). '
                                 'You cannot use them together.')
            if self.settings.output_path is None:
                self.settings.output_path = self.settings._destination
            if self.settings.output_path == '-':  # use stdout
                self.settings.output_path = None
        self.settings._destination = self.settings.output \
            = self.settings.output_path

        self.destination = self.destination_class(
            destination=destination,
            destination_path=self.settings.output_path,
            encoding=self.settings.output_encoding,
            error_handler=self.settings.output_encoding_error_handler)

    def apply_transforms(self) -> None:
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
        exit_ = None
        try:
            if self.settings is None:
                self.process_command_line(
                    argv, usage, description, settings_spec, config_section,
                    **(settings_overrides or {}))
            self.set_io()
            self.prompt()
            self.document = self.reader.read(self.source, self.parser,
                                             self.settings)
            self.apply_transforms()
            output = self.writer.write(self.document, self.destination)
            self.writer.assemble_parts()
        except SystemExit as error:
            exit_ = True
            exit_status = error.code
        except Exception as error:
            if not self.settings:       # exception too early to report nicely
                raise
            if self.settings.traceback:  # Propagate exceptions?
                self.debugging_dumps()
                raise
            self.report_Exception(error)
            exit_ = True
            exit_status = 1
        self.debugging_dumps()
        if (enable_exit_status and self.document
            and (self.document.reporter.max_level
                 >= self.settings.exit_status_level)):
            sys.exit(self.document.reporter.max_level + 10)
        elif exit_:
            sys.exit(exit_status)
        return output

    def debugging_dumps(self) -> None:
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
            print(' (priority, transform class, pending node details, '
                  'keyword args)', file=self._stderr)
            print(pprint.pformat(
                [(priority, '%s.%s' % (xclass.__module__, xclass.__name__),
                  pending and pending.details, kwargs)
                 for priority, xclass, pending, kwargs
                 in self.document.transformer.applied]), file=self._stderr)
        if self.settings.dump_pseudo_xml:
            print('\n::: Pseudo-XML:', file=self._stderr)
            print(self.document.pformat().encode(
                'raw_unicode_escape'), file=self._stderr)

    def prompt(self) -> None:
        """Print info and prompt when waiting for input from a terminal."""
        try:
            if not (self.source.isatty() and self._stderr.isatty()):
                return
        except AttributeError:
            return
        eot_key = 'Ctrl+Z' if os.name == 'nt' else 'Ctrl+D'
        in_format = ''
        out_format = 'useful formats'
        try:
            in_format = self.parser.supported[0]
            out_format = self.writer.supported[0]
        except (AttributeError, IndexError):
            pass
        print(f'Docutils {__version__} <https://docutils.sourceforge.io>\n'
              f'converting "{in_format}" into "{out_format}".\n'
              f'Call with option "--help" for more info.\n'
              f'.. Waiting for source text (finish with {eot_key} '
              'on an empty line):',
              file=self._stderr)

    def report_Exception(self, error) -> None:
        if isinstance(error, utils.SystemMessage):
            self.report_SystemMessage(error)
        elif isinstance(error, UnicodeEncodeError):
            self.report_UnicodeError(error)
        elif isinstance(error, io.InputError):
            self._stderr.write('Unable to open source file for reading:\n'
                               '  %s\n' % io.error_string(error))
        elif isinstance(error, io.OutputError):
            self._stderr.write(
                'Unable to open destination file for writing:\n'
                '  %s\n' % io.error_string(error))
        else:
            print('%s' % io.error_string(error), file=self._stderr)
            print(f"""\
Exiting due to error.  Use "--traceback" to diagnose.
Please report errors to <docutils-users@lists.sourceforge.net>.
Include "--traceback" output, Docutils version ({__version__}\
{f' [{__version_details__}]' if __version_details__ else ''}),
Python version ({sys.version.split()[0]}), your OS type & version, \
and the command line used.""", file=self._stderr)

    def report_SystemMessage(self, error) -> None:
        print('Exiting due to level-%s (%s) system message.' % (
                  error.level, utils.Reporter.levels[error.level]),
              file=self._stderr)

    def report_UnicodeError(self, error) -> None:
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
            'please report it to <docutils-users@lists.sourceforge.net>.\n'
            'Include "--traceback" output, Docutils version (%s),\n'
            'Python version (%s), your OS type & version, and the\n'
            'command line used.\n'
            % (io.error_string(error),
               self.settings.output_encoding,
               data.encode('ascii', 'xmlcharrefreplace'),
               data.encode('ascii', 'backslashreplace'),
               self.settings.output_encoding_error_handler,
               __version__, sys.version.split()[0]))


default_usage = '%prog [options] [<source> [<destination>]]'
default_description = (
    'Reads from <source> (default is stdin) '
    'and writes to <destination> (default is stdout).  '
    'See https://docutils.sourceforge.io/docs/user/config.html '
    'for a detailed settings reference.')


# TODO: or not to do?  cf. https://clig.dev/#help
#
# Display output on success, but keep it brief.
# Provide a -q option to suppress all non-essential output.
#
# Chain several args as input and use --output or redirection for output:
#   argparser.add_argument('source', nargs='+')
#
def publish_cmdline(reader=None, reader_name=None,
                    parser=None, parser_name=None,
                    writer=None, writer_name=None,
                    settings=None, settings_spec=None,
                    settings_overrides=None, config_section=None,
                    enable_exit_status=True, argv=None,
                    usage=default_usage, description=default_description):
    """
    Set up & run a `Publisher` for command-line-based file I/O (input and
    output file paths taken automatically from the command line).
    Also return the output as `str` or `bytes` (for binary output document
    formats).

    Parameters: see `publish_programmatically()` for the remainder.

    - `argv`: Command-line argument list to use instead of ``sys.argv[1:]``.
    - `usage`: Usage string, output if there's a problem parsing the command
      line.
    - `description`: Program description, output for the "--help" option
      (along with command-line option descriptions).
    """
    # The "*_name" arguments are deprecated.
    _name_arg_warning(reader_name, parser_name, writer_name)
    # The default is only used if both arguments are empty
    reader = reader or reader_name or 'standalone'
    parser = parser or parser_name or 'restructuredtext'
    writer = writer or writer_name or 'pseudoxml'
    publisher = Publisher(reader, parser, writer, settings=settings)
    output = publisher.publish(
        argv, usage, description, settings_spec, settings_overrides,
        config_section=config_section, enable_exit_status=enable_exit_status)
    return output


def publish_file(source=None, source_path=None,
                 destination=None, destination_path=None,
                 reader=None, reader_name=None,
                 parser=None, parser_name=None,
                 writer=None, writer_name=None,
                 settings=None, settings_spec=None, settings_overrides=None,
                 config_section=None, enable_exit_status=False):
    """
    Set up & run a `Publisher` for programmatic use with file-like I/O.
    Also return the output as `str` or `bytes` (for binary output document
    formats).

    Parameters: see `publish_programmatically()`.
    """
    # The "*_name" arguments are deprecated.
    _name_arg_warning(reader_name, parser_name, writer_name)
    # The default is set in publish_programmatically().
    output, _publisher = publish_programmatically(
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
                   reader=None, reader_name=None,
                   parser=None, parser_name=None,
                   writer=None, writer_name=None,
                   settings=None, settings_spec=None,
                   settings_overrides=None, config_section=None,
                   enable_exit_status=False):
    """
    Set up & run a `Publisher` for programmatic use with string I/O.

    Accepts a `bytes` or `str` instance as `source`.

    The output is encoded according to the `output_encoding`_ setting;
    the return value is a `bytes` instance (unless `output_encoding`_ is
    "unicode", cf. `docutils.io.StringOutput.write()`).

    Parameters: see `publish_programmatically()` or
    https://docutils.sourceforge.io/docs/api/publisher.html#publish-string

    This function is provisional because in Python 3 name and behaviour
    no longer match.

    .. _output_encoding:
        https://docutils.sourceforge.io/docs/user/config.html#output-encoding
    """
    # The "*_name" arguments are deprecated.
    _name_arg_warning(reader_name, parser_name, writer_name)
    # The default is set in publish_programmatically().
    output, _publisher = publish_programmatically(
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
                  reader=None, reader_name=None,
                  parser=None, parser_name=None,
                  writer=None, writer_name=None,
                  settings=None, settings_spec=None,
                  settings_overrides=None, config_section=None,
                  enable_exit_status=False):
    """
    Set up & run a `Publisher`, and return a dictionary of document parts.

    Dictionary keys are the names of parts.
    Dictionary values are `str` instances; encoding is up to the client,
    e.g.::

       parts = publish_parts(...)
       body = parts['body'].encode(parts['encoding'], parts['errors'])

    See the `API documentation`__ for details on the provided parts.

    Parameters: see `publish_programmatically()`.

    __ https://docutils.sourceforge.io/docs/api/publisher.html#publish-parts
    """
    # The "*_name" arguments are deprecated.
    _name_arg_warning(reader_name, parser_name, writer_name)
    # The default is set in publish_programmatically().
    _output, publisher = publish_programmatically(
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
    return publisher.writer.parts


def publish_doctree(source, source_path=None,
                    source_class=io.StringInput,
                    reader=None, reader_name=None,
                    parser=None, parser_name=None,
                    settings=None, settings_spec=None,
                    settings_overrides=None, config_section=None,
                    enable_exit_status=False):
    """
    Set up & run a `Publisher` for programmatic use. Return a document tree.

    Parameters: see `publish_programmatically()`.
    """
    # The "*_name" arguments are deprecated.
    _name_arg_warning(reader_name, parser_name, None)
    # The default is set in publish_programmatically().
    _output, publisher = publish_programmatically(
        source=source, source_path=source_path,
        source_class=source_class,
        destination=None, destination_path=None,
        destination_class=io.NullOutput,
        reader=reader, reader_name=reader_name,
        parser=parser, parser_name=parser_name,
        writer='null', writer_name=None,
        settings=settings, settings_spec=settings_spec,
        settings_overrides=settings_overrides, config_section=config_section,
        enable_exit_status=enable_exit_status)
    return publisher.document


def publish_from_doctree(document, destination_path=None,
                         writer=None, writer_name=None,
                         settings=None, settings_spec=None,
                         settings_overrides=None, config_section=None,
                         enable_exit_status=False):
    """
    Set up & run a `Publisher` to render from an existing document tree
    data structure. For programmatic use with string output
    (`bytes` or `str`, cf. `publish_string()`).

    Note that ``document.settings`` is overridden; if you want to use the
    settings of the original `document`, pass ``settings=document.settings``.

    Also, new `document.transformer` and `document.reporter` objects are
    generated.

    Parameters: `document` is a `docutils.nodes.document` object, an existing
    document tree.

    Other parameters: see `publish_programmatically()`.

    This function is provisional because in Python 3 name and behaviour
    of the `io.StringOutput` class no longer match.
    """
    # The "writer_name" argument is deprecated.
    _name_arg_warning(None, None, writer_name)
    publisher = Publisher(reader=doctree.Reader(),
                          writer=writer or writer_name or 'pseudoxml',
                          source=io.DocTreeInput(document),
                          destination_class=io.StringOutput,
                          settings=settings)
    publisher.process_programmatic_settings(
        settings_spec, settings_overrides, config_section)
    publisher.set_destination(None, destination_path)
    return publisher.publish(enable_exit_status=enable_exit_status)


def publish_cmdline_to_binary(reader=None, reader_name='standalone',
                              parser=None, parser_name='restructuredtext',
                              writer=None, writer_name='pseudoxml',
                              settings=None,
                              settings_spec=None,
                              settings_overrides=None,
                              config_section=None,
                              enable_exit_status=True,
                              argv=None,
                              usage=default_usage,
                              description=default_description,
                              destination=None,
                              destination_class=io.BinaryFileOutput):
    """
    Set up & run a `Publisher` for command-line-based file I/O (input and
    output file paths taken automatically from the command line).
    Also return the output as `bytes`.

    This is just like publish_cmdline, except that it uses
    io.BinaryFileOutput instead of io.FileOutput.

    Parameters: see `publish_programmatically()` for the remainder.

    - `argv`: Command-line argument list to use instead of ``sys.argv[1:]``.
    - `usage`: Usage string, output if there's a problem parsing the command
      line.
    - `description`: Program description, output for the "--help" option
      (along with command-line option descriptions).

    Deprecated. Use `publish_cmdline()` (works with `bytes` since
    Docutils 0.20). Will be removed in Docutils 0.24.
    """
    warnings.warn('"publish_cmdline_to_binary()" is obsoleted'
                  ' by "publish_cmdline()" and will be removed'
                  ' in Docutils 0.24.', DeprecationWarning, stacklevel=2)
    publisher = Publisher(reader, parser, writer, settings=settings,
                          destination_class=destination_class)
    publisher.set_components(reader_name, parser_name, writer_name)
    output = publisher.publish(
        argv, usage, description, settings_spec, settings_overrides,
        config_section=config_section, enable_exit_status=enable_exit_status)
    return output


def _name_arg_warning(*name_args) -> None:
    for component, name_arg in zip(('reader', 'parser', 'writer'), name_args):
        if name_arg is not None:
            warnings.warn(f'Argument "{component}_name" will be removed in '
                          f'Docutils 2.0.  Specify {component} name '
                          f'in the "{component}" argument.',
                          PendingDeprecationWarning, stacklevel=3)


def publish_programmatically(source_class, source, source_path,
                             destination_class, destination, destination_path,
                             reader, reader_name,
                             parser, parser_name,
                             writer, writer_name,
                             settings, settings_spec,
                             settings_overrides, config_section,
                             enable_exit_status):
    """
    Set up & run a `Publisher` for custom programmatic use.

    Return the output (as `str` or `bytes`, depending on `destination_class`,
    writer, and the "output_encoding" setting) and the Publisher object.

    Internal:
    Applications should not call this function directly.  If it does
    seem to be necessary to call this function directly, please write to the
    Docutils-develop mailing list
    <https://docutils.sourceforge.io/docs/user/mailing-lists.html#docutils-develop>.

    Parameters:

    * `source_class` **required**: The class for dynamically created source
      objects.  Typically `io.FileInput` or `io.StringInput`.

    * `source`: Type depends on `source_class`:

      - If `source_class` is `io.FileInput`: Either a file-like object
        (must have 'read' and 'close' methods), or ``None``
        (`source_path` is opened).  If neither `source` nor
        `source_path` are supplied, `sys.stdin` is used.

      - If `source_class` is `io.StringInput` **required**:
        The input as either a `bytes` object (ensure the 'input_encoding'
        setting matches its encoding) or a `str` object.

    * `source_path`: Type depends on `source_class`:

      - `io.FileInput`: Path to the input file, opened if no `source`
        supplied.

      - `io.StringInput`: Optional.  Path to the file or description of the
        object that produced `source`.  Only used for diagnostic output.

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

    * `reader`: A `docutils.readers.Reader` instance, name, or alias.
      Default: "standalone".

    * `reader_name`: Deprecated. Use `reader`.

    * `parser`: A `docutils.parsers.Parser` instance, name, or alias.
      Default: "restructuredtext".

    * `parser_name`: Deprecated. Use `parser`.

    * `writer`: A `docutils.writers.Writer` instance, name, or alias.
      Default: "pseudoxml".

    * `writer_name`: Deprecated. Use `writer`.

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
    reader = reader or reader_name or 'standalone'
    parser = parser or parser_name or 'restructuredtext'
    writer = writer or writer_name or 'pseudoxml'

    publisher = Publisher(reader, parser, writer, settings=settings,
                          source_class=source_class,
                          destination_class=destination_class)
    publisher.process_programmatic_settings(
        settings_spec, settings_overrides, config_section)
    publisher.set_source(source, source_path)
    publisher.set_destination(destination, destination_path)
    output = publisher.publish(enable_exit_status=enable_exit_status)
    return output, publisher


# "Entry points" with functionality of the "tools/rst2*.py" scripts
# cf. https://packaging.python.org/en/latest/specifications/entry-points/

def rst2something(writer, documenttype, doc_path='') -> None:
    # Helper function for the common parts of `rst2*()`
    #   writer:       writer name
    #   documenttype: output document type
    #   doc_path:     documentation path (relative to the documentation root)
    description = (
        f'Generate {documenttype} documents '
        'from standalone reStructuredText sources '
        f'<https://docutils.sourceforge.io/docs/{doc_path}>.  '
        + default_description)
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error as e:
        sys.stderr.write(f'WARNING: Cannot set the default locale: {e}.\n')
    publish_cmdline(writer=writer, description=description)


def rst2html() -> None:
    rst2something('html', 'HTML', 'user/html.html#html')


def rst2html4() -> None:
    rst2something('html4', 'XHTML 1.1', 'user/html.html#html4css1')


def rst2html5() -> None:
    rst2something('html5', 'HTML5', 'user/html.html#html5-polyglot')


def rst2latex() -> None:
    rst2something('latex', 'LaTeX', 'user/latex.html')


def rst2man() -> None:
    rst2something('manpage', 'Unix manual (troff)', 'user/manpage.html')


def rst2odt() -> None:
    rst2something('odt', 'OpenDocument text (ODT)', 'user/odt.html')


def rst2pseudoxml() -> None:
    rst2something('pseudoxml', 'pseudo-XML (test)', 'ref/doctree.html')


def rst2s5() -> None:
    rst2something('s5', 'S5 HTML slideshow', 'user/slide-shows.html')


def rst2xetex() -> None:
    rst2something('xetex', 'LaTeX (XeLaTeX/LuaLaTeX)', 'user/latex.html')


def rst2xml() -> None:
    rst2something('xml', 'Docutils-native XML', 'ref/doctree.html')
