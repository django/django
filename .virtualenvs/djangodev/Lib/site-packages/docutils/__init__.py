# $Id: __init__.py 9649 2024-04-23 18:54:26Z grubert $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
This is the Docutils (Python Documentation Utilities) package.

Package Structure
=================

Modules:

- __init__.py: Contains component base classes, exception classes, and
  Docutils version information.

- core.py: Contains the ``Publisher`` class and ``publish_*()`` convenience
  functions.

- frontend.py: Runtime settings (command-line interface, configuration files)
  processing, for Docutils front-ends.

- io.py: Provides a uniform API for low-level input and output.

- nodes.py: Docutils document tree (doctree) node class library.

- statemachine.py: A finite state machine specialized for
  regular-expression-based text filters.

Subpackages:

- languages: Language-specific mappings of terms.

- parsers: Syntax-specific input parser modules or packages.

- readers: Context-specific input handlers which understand the data
  source and manage a parser.

- transforms: Modules used by readers and writers to modify
  the Docutils document tree.

- utils: Contains the ``Reporter`` system warning class and miscellaneous
  utilities used by readers, writers, and transforms.

  utils/urischemes.py: Contains a complete mapping of known URI addressing
  scheme names to descriptions.

- utils/math: Contains functions for conversion of mathematical notation
  between different formats (LaTeX, MathML, text, ...).

- writers: Format-specific output translators.
"""

from collections import namedtuple

__docformat__ = 'reStructuredText'

__version__ = '0.21.2'
"""Docutils version identifier (complies with PEP 440)::

    major.minor[.micro][releaselevel[serial]][.dev]

For version comparison operations, use `__version_info__` (see, below)
rather than parsing the text of `__version__`.

https://docutils.sourceforge.io/docs/dev/policies.html#version-identification
"""

__version_details__ = ''
"""Optional extra version details (e.g. 'snapshot 2005-05-29, r3410').

For development and release status, use `__version__ and `__version_info__`.
"""


class VersionInfo(namedtuple('VersionInfo',
                             'major minor micro releaselevel serial release')):

    def __new__(cls, major=0, minor=0, micro=0,
                releaselevel='final', serial=0, release=True):
        releaselevels = ('alpha', 'beta', 'candidate', 'final')
        if releaselevel not in releaselevels:
            raise ValueError('releaselevel must be one of %r.'
                             % (releaselevels, ))
        if releaselevel == 'final':
            if not release:
                raise ValueError('releaselevel "final" must not be used '
                                 'with development versions (leads to wrong '
                                 'version ordering of the related __version__')
                # cf. https://peps.python.org/pep-0440/#summary-of-permitted-suffixes-and-relative-ordering  # noqa
            if serial != 0:
                raise ValueError('"serial" must be 0 for final releases')

        return super().__new__(cls, major, minor, micro,
                               releaselevel, serial, release)

    def __lt__(self, other):
        if isinstance(other, tuple):
            other = VersionInfo(*other)
        return tuple.__lt__(self, other)

    def __gt__(self, other):
        if isinstance(other, tuple):
            other = VersionInfo(*other)
        return tuple.__gt__(self, other)

    def __le__(self, other):
        if isinstance(other, tuple):
            other = VersionInfo(*other)
        return tuple.__le__(self, other)

    def __ge__(self, other):
        if isinstance(other, tuple):
            other = VersionInfo(*other)
        return tuple.__ge__(self, other)


__version_info__ = VersionInfo(
    major=0,
    minor=21,
    micro=2,
    releaselevel='final',  # one of 'alpha', 'beta', 'candidate', 'final'
    serial=0,  # pre-release number (0 for final releases and snapshots)
    release=True  # True for official releases and pre-releases
    )
"""Comprehensive version information tuple.

https://docutils.sourceforge.io/docs/dev/policies.html#version-identification
"""


class ApplicationError(Exception): pass
class DataError(ApplicationError): pass


class SettingsSpec:

    """
    Runtime setting specification base class.

    SettingsSpec subclass objects used by `docutils.frontend.OptionParser`.
    """

    # TODO: replace settings_specs with a new data structure
    # Backwards compatiblity:
    #   Drop-in components:
    #   Sphinx supplies settings_spec in the current format in some places
    #   Myst parser provides a settings_spec tuple
    #
    #   Sphinx reads a settings_spec in order to set a default value
    #   in writers/html.py:59
    #   https://github.com/sphinx-doc/sphinx/blob/4.x/sphinx/writers/html.py
    #   This should be changed (before retiring the old format)
    #   to use `settings_default_overrides` instead.
    settings_spec = ()
    """Runtime settings specification.  Override in subclasses.

    Defines runtime settings and associated command-line options, as used by
    `docutils.frontend.OptionParser`.  This is a tuple of:

    - Option group title (string or `None` which implies no group, just a list
      of single options).

    - Description (string or `None`).

    - A sequence of option tuples.  Each consists of:

      - Help text (string)

      - List of option strings (e.g. ``['-Q', '--quux']``).

      - Dictionary of keyword arguments sent to the OptionParser/OptionGroup
        ``add_option`` method.

        Runtime setting names are derived implicitly from long option names
        ('--a-setting' becomes ``settings.a_setting``) or explicitly from the
        'dest' keyword argument.

        Most settings will also have a 'validator' keyword & function.  The
        validator function validates setting values (from configuration files
        and command-line option arguments) and converts them to appropriate
        types.  For example, the ``docutils.frontend.validate_boolean``
        function, **required by all boolean settings**, converts true values
        ('1', 'on', 'yes', and 'true') to 1 and false values ('0', 'off',
        'no', 'false', and '') to 0.  Validators need only be set once per
        setting.  See the `docutils.frontend.validate_*` functions.

        See the optparse docs for more details.

    - More triples of group title, description, options, as many times as
      needed.  Thus, `settings_spec` tuples can be simply concatenated.
    """

    settings_defaults = None
    """A dictionary of defaults for settings not in `settings_spec` (internal
    settings, intended to be inaccessible by command-line and config file).
    Override in subclasses."""

    settings_default_overrides = None
    """A dictionary of auxiliary defaults, to override defaults for settings
    defined in other components' `setting_specs`.  Override in subclasses."""

    relative_path_settings = ()
    """Settings containing filesystem paths.  Override in subclasses.
    Settings listed here are to be interpreted relative to the current working
    directory."""

    config_section = None
    """The name of the config file section specific to this component
    (lowercase, no brackets).  Override in subclasses."""

    config_section_dependencies = None
    """A list of names of config file sections that are to be applied before
    `config_section`, in order (from general to specific).  In other words,
    the settings in `config_section` are to be overlaid on top of the settings
    from these sections.  The "general" section is assumed implicitly.
    Override in subclasses."""


class TransformSpec:
    """
    Runtime transform specification base class.

    Provides the interface to register "transforms" and helper functions
    to resolve references with a `docutils.transforms.Transformer`.

    https://docutils.sourceforge.io/docs/ref/transforms.html
    """

    def get_transforms(self):
        """Transforms required by this class.  Override in subclasses."""
        if self.default_transforms != ():
            import warnings
            warnings.warn('TransformSpec: the "default_transforms" attribute '
                          'will be removed in Docutils 2.0.\n'
                          'Use get_transforms() method instead.',
                          DeprecationWarning)
            return list(self.default_transforms)
        return []

    # Deprecated; for compatibility.
    default_transforms = ()

    unknown_reference_resolvers = ()
    """List of functions to try to resolve unknown references.

    Unknown references have a 'refname' attribute which doesn't correspond
    to any target in the document.  Called when the transforms in
    `docutils.transforms.references` are unable to find a correct target.

    The list should contain functions which will try to resolve unknown
    references, with the following signature::

        def reference_resolver(node):
            '''Returns boolean: true if resolved, false if not.'''

    If the function is able to resolve the reference, it should also remove
    the 'refname' attribute and mark the node as resolved::

        del node['refname']
        node.resolved = 1

    Each function must have a "priority" attribute which will affect the order
    the unknown_reference_resolvers are run::

        reference_resolver.priority = 100

    This hook is provided for 3rd party extensions.
    Example use case: the `MoinMoin - ReStructured Text Parser`
    in ``sandbox/mmgilbe/rst.py``.
    """


class Component(SettingsSpec, TransformSpec):

    """Base class for Docutils components."""

    component_type = None
    """Name of the component type ('reader', 'parser', 'writer').  Override in
    subclasses."""

    supported = ()
    """Name and aliases for this component.  Override in subclasses."""

    def supports(self, format):
        """
        Is `format` supported by this component?

        To be used by transforms to ask the dependent component if it supports
        a certain input context or output format.
        """
        return format in self.supported
