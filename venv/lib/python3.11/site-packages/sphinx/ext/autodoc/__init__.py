"""Extension to create automatic documentation from code docstrings.

Automatically insert docstrings for functions, classes or whole modules into
the doctree, thus avoiding duplication between docstrings and documentation
for those who like elaborate docstrings.
"""

from __future__ import annotations

import re
import sys
import warnings
from inspect import Parameter, Signature
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from docutils.statemachine import StringList

import sphinx
from sphinx.config import ENUM, Config
from sphinx.deprecation import RemovedInSphinx80Warning
from sphinx.ext.autodoc.importer import get_class_members, import_module, import_object
from sphinx.ext.autodoc.mock import ismock, mock, undecorate
from sphinx.locale import _, __
from sphinx.pycode import ModuleAnalyzer, PycodeError
from sphinx.util import inspect, logging
from sphinx.util.docstrings import prepare_docstring, separate_metadata
from sphinx.util.inspect import (
    evaluate_signature,
    getdoc,
    object_description,
    safe_getattr,
    stringify_signature,
)
from sphinx.util.typing import OptionSpec, get_type_hints, restify, stringify_annotation

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from types import ModuleType

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.ext.autodoc.directive import DocumenterBridge

logger = logging.getLogger(__name__)


# This type isn't exposed directly in any modules, but can be found
# here in most Python versions
MethodDescriptorType = type(type.__subclasses__)


#: extended signature RE: with explicit module name separated by ::
py_ext_sig_re = re.compile(
    r'''^ ([\w.]+::)?            # explicit module name
          ([\w.]+\.)?            # module and/or class name(s)
          (\w+)  \s*             # thing name
          (?: \[\s*(.*)\s*])?    # optional: type parameters list
          (?: \((.*)\)           # optional: arguments
           (?:\s* -> \s* (.*))?  #           return annotation
          )? $                   # and nothing more
          ''', re.VERBOSE)
special_member_re = re.compile(r'^__\S+__$')


def identity(x: Any) -> Any:
    return x


class _All:
    """A special value for :*-members: that matches to any member."""

    def __contains__(self, item: Any) -> bool:
        return True

    def append(self, item: Any) -> None:
        pass  # nothing


class _Empty:
    """A special value for :exclude-members: that never matches to any member."""

    def __contains__(self, item: Any) -> bool:
        return False


ALL = _All()
EMPTY = _Empty()
UNINITIALIZED_ATTR = object()
INSTANCEATTR = object()
SLOTSATTR = object()


def members_option(arg: Any) -> object | list[str]:
    """Used to convert the :members: option to auto directives."""
    if arg in (None, True):
        return ALL
    elif arg is False:
        return None
    else:
        return [x.strip() for x in arg.split(',') if x.strip()]


def exclude_members_option(arg: Any) -> object | set[str]:
    """Used to convert the :exclude-members: option."""
    if arg in (None, True):
        return EMPTY
    return {x.strip() for x in arg.split(',') if x.strip()}


def inherited_members_option(arg: Any) -> set[str]:
    """Used to convert the :inherited-members: option to auto directives."""
    if arg in (None, True):
        return {'object'}
    elif arg:
        return {x.strip() for x in arg.split(',')}
    else:
        return set()


def member_order_option(arg: Any) -> str | None:
    """Used to convert the :member-order: option to auto directives."""
    if arg in (None, True):
        return None
    elif arg in ('alphabetical', 'bysource', 'groupwise'):
        return arg
    else:
        raise ValueError(__('invalid value for member-order option: %s') % arg)


def class_doc_from_option(arg: Any) -> str | None:
    """Used to convert the :class-doc-from: option to autoclass directives."""
    if arg in ('both', 'class', 'init'):
        return arg
    else:
        raise ValueError(__('invalid value for class-doc-from option: %s') % arg)


SUPPRESS = object()


def annotation_option(arg: Any) -> Any:
    if arg in (None, True):
        # suppress showing the representation of the object
        return SUPPRESS
    else:
        return arg


def bool_option(arg: Any) -> bool:
    """Used to convert flag options to auto directives.  (Instead of
    directives.flag(), which returns None).
    """
    return True


def merge_members_option(options: dict) -> None:
    """Merge :private-members: and :special-members: options to the
    :members: option.
    """
    if options.get('members') is ALL:
        # merging is not needed when members: ALL
        return

    members = options.setdefault('members', [])
    for key in {'private-members', 'special-members'}:
        if key in options and options[key] not in (ALL, None):
            for member in options[key]:
                if member not in members:
                    members.append(member)


# Some useful event listener factories for autodoc-process-docstring.

def cut_lines(pre: int, post: int = 0, what: str | None = None) -> Callable:
    """Return a listener that removes the first *pre* and last *post*
    lines of every docstring.  If *what* is a sequence of strings,
    only docstrings of a type in *what* will be processed.

    Use like this (e.g. in the ``setup()`` function of :file:`conf.py`)::

       from sphinx.ext.autodoc import cut_lines
       app.connect('autodoc-process-docstring', cut_lines(4, what=['module']))

    This can (and should) be used in place of :confval:`automodule_skip_lines`.
    """
    def process(app: Sphinx, what_: str, name: str, obj: Any, options: Any, lines: list[str],
                ) -> None:
        if what and what_ not in what:
            return
        del lines[:pre]
        if post:
            # remove one trailing blank line.
            if lines and not lines[-1]:
                lines.pop(-1)
            del lines[-post:]
        # make sure there is a blank line at the end
        if lines and lines[-1]:
            lines.append('')
    return process


def between(
    marker: str,
    what: Sequence[str] | None = None,
    keepempty: bool = False,
    exclude: bool = False,
) -> Callable:
    """Return a listener that either keeps, or if *exclude* is True excludes,
    lines between lines that match the *marker* regular expression.  If no line
    matches, the resulting docstring would be empty, so no change will be made
    unless *keepempty* is true.

    If *what* is a sequence of strings, only docstrings of a type in *what* will
    be processed.
    """
    marker_re = re.compile(marker)

    def process(app: Sphinx, what_: str, name: str, obj: Any, options: Any, lines: list[str],
                ) -> None:
        if what and what_ not in what:
            return
        deleted = 0
        delete = not exclude
        orig_lines = lines[:]
        for i, line in enumerate(orig_lines):
            if delete:
                lines.pop(i - deleted)
                deleted += 1
            if marker_re.match(line):
                delete = not delete
                if delete:
                    lines.pop(i - deleted)
                    deleted += 1
        if not lines and not keepempty:
            lines[:] = orig_lines
        # make sure there is a blank line at the end
        if lines and lines[-1]:
            lines.append('')
    return process


# This class is used only in ``sphinx.ext.autodoc.directive``,
# But we define this class here to keep compatibility (see #4538)
class Options(dict):
    """A dict/attribute hybrid that returns None on nonexisting keys."""
    def copy(self) -> Options:
        return Options(super().copy())

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name.replace('_', '-')]
        except KeyError:
            return None


class ObjectMember:
    """A member of object.

    This is used for the result of `Documenter.get_module_members()` to
    represent each member of the object.

    .. Note::

       An instance of this class behaves as a tuple of (name, object)
       for compatibility to old Sphinx.  The behavior will be dropped
       in the future.  Therefore extensions should not use the tuple
       interface.
    """

    def __init__(self, name: str, obj: Any, *, docstring: str | None = None,
                 class_: Any = None, skipped: bool = False) -> None:
        self.__name__ = name
        self.object = obj
        self.docstring = docstring
        self.skipped = skipped
        self.class_ = class_

    def __getitem__(self, index):
        warnings.warn('The tuple interface of ObjectMember is deprecated. '
                      'Use (obj.__name__, obj.object) instead.',
                      RemovedInSphinx80Warning, stacklevel=2)
        return (self.__name__, self.object)[index]


class Documenter:
    """
    A Documenter knows how to autodocument a single object type.  When
    registered with the AutoDirective, it will be used to document objects
    of that type when needed by autodoc.

    Its *objtype* attribute selects what auto directive it is assigned to
    (the directive name is 'auto' + objtype), and what directive it generates
    by default, though that can be overridden by an attribute called
    *directivetype*.

    A Documenter has an *option_spec* that works like a docutils directive's;
    in fact, it will be used to parse an auto directive's options that matches
    the Documenter.
    """
    #: name by which the directive is called (auto...) and the default
    #: generated directive name
    objtype = 'object'
    #: indentation by which to indent the directive content
    content_indent = '   '
    #: priority if multiple documenters return True from can_document_member
    priority = 0
    #: order if autodoc_member_order is set to 'groupwise'
    member_order = 0
    #: true if the generated content may contain titles
    titles_allowed = True

    option_spec: OptionSpec = {
        'no-index': bool_option,
        'noindex': bool_option,
    }

    def get_attr(self, obj: Any, name: str, *defargs: Any) -> Any:
        """getattr() override for types such as Zope interfaces."""
        return autodoc_attrgetter(self.env.app, obj, name, *defargs)

    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any,
                            ) -> bool:
        """Called to see if a member can be documented by this Documenter."""
        msg = 'must be implemented in subclasses'
        raise NotImplementedError(msg)

    def __init__(self, directive: DocumenterBridge, name: str, indent: str = '') -> None:
        self.directive = directive
        self.config: Config = directive.env.config
        self.env: BuildEnvironment = directive.env
        self.options = directive.genopt
        self.name = name
        self.indent = indent
        # the module and object path within the module, and the fully
        # qualified name (all set after resolve_name succeeds)
        self.modname: str = ''
        self.module: ModuleType | None = None
        self.objpath: list[str] = []
        self.fullname = ''
        # extra signature items (arguments and return annotation,
        # also set after resolve_name succeeds)
        self.args: str | None = None
        self.retann: str = ''
        # the object to document (set after import_object succeeds)
        self.object: Any = None
        self.object_name = ''
        # the parent/owner of the object to document
        self.parent: Any = None
        # the module analyzer to get at attribute docs, or None
        self.analyzer: ModuleAnalyzer | None = None

    @property
    def documenters(self) -> dict[str, type[Documenter]]:
        """Returns registered Documenter classes"""
        return self.env.app.registry.documenters

    def add_line(self, line: str, source: str, *lineno: int) -> None:
        """Append one line of generated reST to the output."""
        if line.strip():  # not a blank line
            self.directive.result.append(self.indent + line, source, *lineno)
        else:
            self.directive.result.append('', source, *lineno)

    def resolve_name(self, modname: str | None, parents: Any, path: str, base: str,
                     ) -> tuple[str | None, list[str]]:
        """Resolve the module and name of the object to document given by the
        arguments and the current module/class.

        Must return a pair of the module name and a chain of attributes; for
        example, it would return ``('zipfile', ['ZipFile', 'open'])`` for the
        ``zipfile.ZipFile.open`` method.
        """
        msg = 'must be implemented in subclasses'
        raise NotImplementedError(msg)

    def parse_name(self) -> bool:
        """Determine what module to import and what attribute to document.

        Returns True and sets *self.modname*, *self.objpath*, *self.fullname*,
        *self.args* and *self.retann* if parsing and resolving was successful.
        """
        # first, parse the definition -- auto directives for classes and
        # functions can contain a signature which is then used instead of
        # an autogenerated one
        matched = py_ext_sig_re.match(self.name)
        if matched is None:
            logger.warning(__('invalid signature for auto%s (%r)') % (self.objtype, self.name),
                           type='autodoc')
            return False
        explicit_modname, path, base, tp_list, args, retann = matched.groups()

        # support explicit module and class name separation via ::
        if explicit_modname is not None:
            modname = explicit_modname[:-2]
            parents = path.rstrip('.').split('.') if path else []
        else:
            modname = None
            parents = []

        with mock(self.config.autodoc_mock_imports):
            modname, self.objpath = self.resolve_name(modname, parents, path, base)

        if not modname:
            return False

        self.modname = modname
        self.args = args
        self.retann = retann
        self.fullname = ((self.modname or '') +
                         ('.' + '.'.join(self.objpath) if self.objpath else ''))
        return True

    def import_object(self, raiseerror: bool = False) -> bool:
        """Import the object given by *self.modname* and *self.objpath* and set
        it as *self.object*.

        Returns True if successful, False if an error occurred.
        """
        with mock(self.config.autodoc_mock_imports):
            try:
                ret = import_object(self.modname, self.objpath, self.objtype,
                                    attrgetter=self.get_attr,
                                    warningiserror=self.config.autodoc_warningiserror)
                self.module, self.parent, self.object_name, self.object = ret
                if ismock(self.object):
                    self.object = undecorate(self.object)
                return True
            except ImportError as exc:
                if raiseerror:
                    raise
                logger.warning(exc.args[0], type='autodoc', subtype='import_object')
                self.env.note_reread()
                return False

    def get_real_modname(self) -> str:
        """Get the real module name of an object to document.

        It can differ from the name of the module through which the object was
        imported.
        """
        return self.get_attr(self.object, '__module__', None) or self.modname

    def check_module(self) -> bool:
        """Check if *self.object* is really defined in the module given by
        *self.modname*.
        """
        if self.options.imported_members:
            return True

        subject = inspect.unpartial(self.object)
        modname = self.get_attr(subject, '__module__', None)
        if modname and modname != self.modname:
            return False
        return True

    def format_args(self, **kwargs: Any) -> str:
        """Format the argument signature of *self.object*.

        Should return None if the object does not have a signature.
        """
        return ''

    def format_name(self) -> str:
        """Format the name of *self.object*.

        This normally should be something that can be parsed by the generated
        directive, but doesn't need to be (Sphinx will display it unparsed
        then).
        """
        # normally the name doesn't contain the module (except for module
        # directives of course)
        return '.'.join(self.objpath) or self.modname

    def _call_format_args(self, **kwargs: Any) -> str:
        if kwargs:
            try:
                return self.format_args(**kwargs)
            except TypeError:
                # avoid chaining exceptions, by putting nothing here
                pass

        # retry without arguments for old documenters
        return self.format_args()

    def format_signature(self, **kwargs: Any) -> str:
        """Format the signature (arguments and return annotation) of the object.

        Let the user process it via the ``autodoc-process-signature`` event.
        """
        if self.args is not None:
            # signature given explicitly
            args = "(%s)" % self.args
            retann = self.retann
        else:
            # try to introspect the signature
            try:
                retann = None
                args = self._call_format_args(**kwargs)
                if args:
                    matched = re.match(r'^(\(.*\))\s+->\s+(.*)$', args)
                    if matched:
                        args = matched.group(1)
                        retann = matched.group(2)
            except Exception as exc:
                logger.warning(__('error while formatting arguments for %s: %s'),
                               self.fullname, exc, type='autodoc')
                args = None

        result = self.env.events.emit_firstresult('autodoc-process-signature',
                                                  self.objtype, self.fullname,
                                                  self.object, self.options, args, retann)
        if result:
            args, retann = result

        if args is not None:
            return args + ((' -> %s' % retann) if retann else '')
        else:
            return ''

    def add_directive_header(self, sig: str) -> None:
        """Add the directive header and options to the generated content."""
        domain = getattr(self, 'domain', 'py')
        directive = getattr(self, 'directivetype', self.objtype)
        name = self.format_name()
        sourcename = self.get_sourcename()

        # one signature per line, indented by column
        prefix = f'.. {domain}:{directive}:: '
        for i, sig_line in enumerate(sig.split("\n")):
            self.add_line(f'{prefix}{name}{sig_line}',
                          sourcename)
            if i == 0:
                prefix = " " * len(prefix)

        if self.options.no_index or self.options.noindex:
            self.add_line('   :no-index:', sourcename)
        if self.objpath:
            # Be explicit about the module, this is necessary since .. class::
            # etc. don't support a prepended module name
            self.add_line('   :module: %s' % self.modname, sourcename)

    def get_doc(self) -> list[list[str]] | None:
        """Decode and return lines of the docstring(s) for the object.

        When it returns None, autodoc-process-docstring will not be called for this
        object.
        """
        docstring = getdoc(self.object, self.get_attr, self.config.autodoc_inherit_docstrings,
                           self.parent, self.object_name)
        if docstring:
            tab_width = self.directive.state.document.settings.tab_width
            return [prepare_docstring(docstring, tab_width)]
        return []

    def process_doc(self, docstrings: list[list[str]]) -> Iterator[str]:
        """Let the user process the docstrings before adding them."""
        for docstringlines in docstrings:
            if self.env.app:
                # let extensions preprocess docstrings
                self.env.app.emit('autodoc-process-docstring',
                                  self.objtype, self.fullname, self.object,
                                  self.options, docstringlines)

                if docstringlines and docstringlines[-1] != '':
                    # append a blank line to the end of the docstring
                    docstringlines.append('')

            yield from docstringlines

    def get_sourcename(self) -> str:
        if (inspect.safe_getattr(self.object, '__module__', None) and
                inspect.safe_getattr(self.object, '__qualname__', None)):
            # Get the correct location of docstring from self.object
            # to support inherited methods
            fullname = f'{self.object.__module__}.{self.object.__qualname__}'
        else:
            fullname = self.fullname

        if self.analyzer:
            return f'{self.analyzer.srcname}:docstring of {fullname}'
        else:
            return 'docstring of %s' % fullname

    def add_content(self, more_content: StringList | None) -> None:
        """Add content from docstrings, attribute documentation and user."""
        docstring = True

        # set sourcename and add content from attribute documentation
        sourcename = self.get_sourcename()
        if self.analyzer:
            attr_docs = self.analyzer.find_attr_docs()
            if self.objpath:
                key = ('.'.join(self.objpath[:-1]), self.objpath[-1])
                if key in attr_docs:
                    docstring = False
                    # make a copy of docstring for attributes to avoid cache
                    # the change of autodoc-process-docstring event.
                    attribute_docstrings = [list(attr_docs[key])]

                    for i, line in enumerate(self.process_doc(attribute_docstrings)):
                        self.add_line(line, sourcename, i)

        # add content from docstrings
        if docstring:
            docstrings = self.get_doc()
            if docstrings is None:
                # Do not call autodoc-process-docstring on get_doc() returns None.
                pass
            else:
                if not docstrings:
                    # append at least a dummy docstring, so that the event
                    # autodoc-process-docstring is fired and can add some
                    # content if desired
                    docstrings.append([])
                for i, line in enumerate(self.process_doc(docstrings)):
                    self.add_line(line, sourcename, i)

        # add additional content (e.g. from document), if present
        if more_content:
            for line, src in zip(more_content.data, more_content.items):
                self.add_line(line, src[0], src[1])

    def get_object_members(self, want_all: bool) -> tuple[bool, list[ObjectMember]]:
        """Return `(members_check_module, members)` where `members` is a
        list of `(membername, member)` pairs of the members of *self.object*.

        If *want_all* is True, return all members.  Else, only return those
        members given by *self.options.members* (which may also be None).
        """
        msg = 'must be implemented in subclasses'
        raise NotImplementedError(msg)

    def filter_members(self, members: list[ObjectMember], want_all: bool,
                       ) -> list[tuple[str, Any, bool]]:
        """Filter the given member list.

        Members are skipped if

        - they are private (except if given explicitly or the private-members
          option is set)
        - they are special methods (except if given explicitly or the
          special-members option is set)
        - they are undocumented (except if the undoc-members option is set)

        The user can override the skipping decision by connecting to the
        ``autodoc-skip-member`` event.
        """
        def is_filtered_inherited_member(name: str, obj: Any) -> bool:
            inherited_members = self.options.inherited_members or set()

            if inspect.isclass(self.object):
                for cls in self.object.__mro__:
                    if cls.__name__ in inherited_members and cls != self.object:
                        # given member is a member of specified *super class*
                        return True
                    if name in cls.__dict__:
                        return False
                    if name in self.get_attr(cls, '__annotations__', {}):
                        return False
                    if isinstance(obj, ObjectMember) and obj.class_ is cls:
                        return False

            return False

        ret = []

        # search for members in source code too
        namespace = '.'.join(self.objpath)  # will be empty for modules

        if self.analyzer:
            attr_docs = self.analyzer.find_attr_docs()
        else:
            attr_docs = {}

        # process members and determine which to skip
        for obj in members:
            try:
                membername = obj.__name__
                member = obj.object
            except AttributeError:
                if isinstance(obj, ObjectMember):
                    raise
                # To be removed, retained for compatibility.
                # See https://github.com/sphinx-doc/sphinx/issues/11631
                membername, member = obj
                warnings.warn(
                    'Returning tuples of (name, object) as '
                    'the second return value from get_object_members() is deprecated. '
                    'Return ObjectMember(name, object) instances instead.',
                    RemovedInSphinx80Warning, stacklevel=2,
                )

            # if isattr is True, the member is documented as an attribute
            isattr = member is INSTANCEATTR or (namespace, membername) in attr_docs

            try:
                doc = getdoc(member, self.get_attr, self.config.autodoc_inherit_docstrings,
                             self.object, membername)
                if not isinstance(doc, str):
                    # Ignore non-string __doc__
                    doc = None

                # if the member __doc__ is the same as self's __doc__, it's just
                # inherited and therefore not the member's doc
                cls = self.get_attr(member, '__class__', None)
                if cls:
                    cls_doc = self.get_attr(cls, '__doc__', None)
                    if cls_doc == doc:
                        doc = None

                if isinstance(obj, ObjectMember) and obj.docstring:
                    # hack for ClassDocumenter to inject docstring via ObjectMember
                    doc = obj.docstring

                doc, metadata = separate_metadata(doc)
                has_doc = bool(doc)

                if 'private' in metadata:
                    # consider a member private if docstring has "private" metadata
                    isprivate = True
                elif 'public' in metadata:
                    # consider a member public if docstring has "public" metadata
                    isprivate = False
                else:
                    isprivate = membername.startswith('_')

                keep = False
                if ismock(member) and (namespace, membername) not in attr_docs:
                    # mocked module or object
                    pass
                elif (self.options.exclude_members and
                      membername in self.options.exclude_members):
                    # remove members given by exclude-members
                    keep = False
                elif want_all and special_member_re.match(membername):
                    # special __methods__
                    if (self.options.special_members and
                            membername in self.options.special_members):
                        if membername == '__doc__':  # NoQA: SIM114
                            keep = False
                        elif is_filtered_inherited_member(membername, obj):
                            keep = False
                        else:
                            keep = has_doc or self.options.undoc_members
                    else:
                        keep = False
                elif (namespace, membername) in attr_docs:
                    if want_all and isprivate:
                        if self.options.private_members is None:
                            keep = False
                        else:
                            keep = membername in self.options.private_members
                    else:
                        # keep documented attributes
                        keep = True
                elif want_all and isprivate:
                    if has_doc or self.options.undoc_members:
                        if self.options.private_members is None:  # NoQA: SIM114
                            keep = False
                        elif is_filtered_inherited_member(membername, obj):
                            keep = False
                        else:
                            keep = membername in self.options.private_members
                    else:
                        keep = False
                else:
                    if (self.options.members is ALL and
                            is_filtered_inherited_member(membername, obj)):
                        keep = False
                    else:
                        # ignore undocumented members if :undoc-members: is not given
                        keep = has_doc or self.options.undoc_members

                if isinstance(obj, ObjectMember) and obj.skipped:
                    # forcedly skipped member (ex. a module attribute not defined in __all__)
                    keep = False

                # give the user a chance to decide whether this member
                # should be skipped
                if self.env.app:
                    # let extensions preprocess docstrings
                    skip_user = self.env.app.emit_firstresult(
                        'autodoc-skip-member', self.objtype, membername, member,
                        not keep, self.options)
                    if skip_user is not None:
                        keep = not skip_user
            except Exception as exc:
                logger.warning(__('autodoc: failed to determine %s.%s (%r) to be documented, '
                                  'the following exception was raised:\n%s'),
                               self.name, membername, member, exc, type='autodoc')
                keep = False

            if keep:
                ret.append((membername, member, isattr))

        return ret

    def document_members(self, all_members: bool = False) -> None:
        """Generate reST for member documentation.

        If *all_members* is True, document all members, else those given by
        *self.options.members*.
        """
        # set current namespace for finding members
        self.env.temp_data['autodoc:module'] = self.modname
        if self.objpath:
            self.env.temp_data['autodoc:class'] = self.objpath[0]

        want_all = (all_members or
                    self.options.inherited_members or
                    self.options.members is ALL)
        # find out which members are documentable
        members_check_module, members = self.get_object_members(want_all)

        # document non-skipped members
        memberdocumenters: list[tuple[Documenter, bool]] = []
        for (mname, member, isattr) in self.filter_members(members, want_all):
            classes = [cls for cls in self.documenters.values()
                       if cls.can_document_member(member, mname, isattr, self)]
            if not classes:
                # don't know how to document this member
                continue
            # prefer the documenter with the highest priority
            classes.sort(key=lambda cls: cls.priority)
            # give explicitly separated module name, so that members
            # of inner classes can be documented
            full_mname = f'{self.modname}::' + '.'.join((*self.objpath, mname))
            documenter = classes[-1](self.directive, full_mname, self.indent)
            memberdocumenters.append((documenter, isattr))

        member_order = self.options.member_order or self.config.autodoc_member_order
        memberdocumenters = self.sort_members(memberdocumenters, member_order)

        for documenter, isattr in memberdocumenters:
            documenter.generate(
                all_members=True, real_modname=self.real_modname,
                check_module=members_check_module and not isattr)

        # reset current objects
        self.env.temp_data['autodoc:module'] = None
        self.env.temp_data['autodoc:class'] = None

    def sort_members(self, documenters: list[tuple[Documenter, bool]],
                     order: str) -> list[tuple[Documenter, bool]]:
        """Sort the given member list."""
        if order == 'groupwise':
            # sort by group; alphabetically within groups
            documenters.sort(key=lambda e: (e[0].member_order, e[0].name))
        elif order == 'bysource':
            # By default, member discovery order matches source order,
            # as dicts are insertion-ordered from Python 3.7.
            if self.analyzer:
                # sort by source order, by virtue of the module analyzer
                tagorder = self.analyzer.tagorder

                def keyfunc(entry: tuple[Documenter, bool]) -> int:
                    fullname = entry[0].name.split('::')[1]
                    return tagorder.get(fullname, len(tagorder))
                documenters.sort(key=keyfunc)
        else:  # alphabetical
            documenters.sort(key=lambda e: e[0].name)

        return documenters

    def generate(
        self,
        more_content: StringList | None = None,
        real_modname: str | None = None,
        check_module: bool = False,
        all_members: bool = False,
    ) -> None:
        """Generate reST for the object given by *self.name*, and possibly for
        its members.

        If *more_content* is given, include that content. If *real_modname* is
        given, use that module name to find attribute docs. If *check_module* is
        True, only generate if the object is defined in the module name it is
        imported from. If *all_members* is True, document all members.
        """
        if not self.parse_name():
            # need a module to import
            logger.warning(
                __("don't know which module to import for autodocumenting "
                   '%r (try placing a "module" or "currentmodule" directive '
                   'in the document, or giving an explicit module name)') %
                self.name, type='autodoc')
            return

        # now, import the module and get object to document
        if not self.import_object():
            return

        # If there is no real module defined, figure out which to use.
        # The real module is used in the module analyzer to look up the module
        # where the attribute documentation would actually be found in.
        # This is used for situations where you have a module that collects the
        # functions and classes of internal submodules.
        guess_modname = self.get_real_modname()
        self.real_modname: str = real_modname or guess_modname

        # try to also get a source code analyzer for attribute docs
        try:
            self.analyzer = ModuleAnalyzer.for_module(self.real_modname)
            # parse right now, to get PycodeErrors on parsing (results will
            # be cached anyway)
            self.analyzer.find_attr_docs()
        except PycodeError as exc:
            logger.debug('[autodoc] module analyzer failed: %s', exc)
            # no source file -- e.g. for builtin and C modules
            self.analyzer = None
            # at least add the module.__file__ as a dependency
            if module___file__ := getattr(self.module, '__file__', ''):
                self.directive.record_dependencies.add(module___file__)
        else:
            self.directive.record_dependencies.add(self.analyzer.srcname)

        if self.real_modname != guess_modname:
            # Add module to dependency list if target object is defined in other module.
            try:
                analyzer = ModuleAnalyzer.for_module(guess_modname)
                self.directive.record_dependencies.add(analyzer.srcname)
            except PycodeError:
                pass

        docstrings: list[str] = sum(self.get_doc() or [], [])
        if ismock(self.object) and not docstrings:
            logger.warning(__('A mocked object is detected: %r'),
                           self.name, type='autodoc')

        # check __module__ of object (for members not given explicitly)
        if check_module:
            if not self.check_module():
                return

        sourcename = self.get_sourcename()

        # make sure that the result starts with an empty line.  This is
        # necessary for some situations where another directive preprocesses
        # reST and no starting newline is present
        self.add_line('', sourcename)

        # format the object's signature, if any
        try:
            sig = self.format_signature()
        except Exception as exc:
            logger.warning(__('error while formatting signature for %s: %s'),
                           self.fullname, exc, type='autodoc')
            return

        # generate the directive header and options, if applicable
        self.add_directive_header(sig)
        self.add_line('', sourcename)

        # e.g. the module directive doesn't have content
        self.indent += self.content_indent

        # add all content (from docstrings, attribute docs etc.)
        self.add_content(more_content)

        # document members, if possible
        self.document_members(all_members)


class ModuleDocumenter(Documenter):
    """
    Specialized Documenter subclass for modules.
    """
    objtype = 'module'
    content_indent = ''
    _extra_indent = '   '

    option_spec: OptionSpec = {
        'members': members_option, 'undoc-members': bool_option,
        'no-index': bool_option, 'inherited-members': inherited_members_option,
        'show-inheritance': bool_option, 'synopsis': identity,
        'platform': identity, 'deprecated': bool_option,
        'member-order': member_order_option, 'exclude-members': exclude_members_option,
        'private-members': members_option, 'special-members': members_option,
        'imported-members': bool_option, 'ignore-module-all': bool_option,
        'no-value': bool_option,
        'noindex': bool_option,
    }

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        merge_members_option(self.options)
        self.__all__: Sequence[str] | None = None

    def add_content(self, more_content: StringList | None) -> None:
        old_indent = self.indent
        self.indent += self._extra_indent
        super().add_content(None)
        self.indent = old_indent
        if more_content:
            for line, src in zip(more_content.data, more_content.items):
                self.add_line(line, src[0], src[1])

    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any,
                            ) -> bool:
        # don't document submodules automatically
        return False

    def resolve_name(self, modname: str | None, parents: Any, path: str, base: str,
                     ) -> tuple[str | None, list[str]]:
        if modname is not None:
            logger.warning(__('"::" in automodule name doesn\'t make sense'),
                           type='autodoc')
        return (path or '') + base, []

    def parse_name(self) -> bool:
        ret = super().parse_name()
        if self.args or self.retann:
            logger.warning(__('signature arguments or return annotation '
                              'given for automodule %s') % self.fullname,
                           type='autodoc')
        return ret

    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror)

        try:
            if not self.options.ignore_module_all:
                self.__all__ = inspect.getall(self.object)
        except ValueError as exc:
            # invalid __all__ found.
            logger.warning(__('__all__ should be a list of strings, not %r '
                              '(in module %s) -- ignoring __all__') %
                           (exc.args[0], self.fullname), type='autodoc')

        return ret

    def add_directive_header(self, sig: str) -> None:
        Documenter.add_directive_header(self, sig)

        sourcename = self.get_sourcename()

        # add some module-specific options
        if self.options.synopsis:
            self.add_line('   :synopsis: ' + self.options.synopsis, sourcename)
        if self.options.platform:
            self.add_line('   :platform: ' + self.options.platform, sourcename)
        if self.options.deprecated:
            self.add_line('   :deprecated:', sourcename)

    def get_module_members(self) -> dict[str, ObjectMember]:
        """Get members of target module."""
        if self.analyzer:
            attr_docs = self.analyzer.attr_docs
        else:
            attr_docs = {}

        members: dict[str, ObjectMember] = {}
        for name in dir(self.object):
            try:
                value = safe_getattr(self.object, name, None)
                if ismock(value):
                    value = undecorate(value)
                docstring = attr_docs.get(('', name), [])
                members[name] = ObjectMember(name, value, docstring="\n".join(docstring))
            except AttributeError:
                continue

        # annotation only member (ex. attr: int)
        for name in inspect.getannotations(self.object):
            if name not in members:
                docstring = attr_docs.get(('', name), [])
                members[name] = ObjectMember(name, INSTANCEATTR,
                                             docstring="\n".join(docstring))

        return members

    def get_object_members(self, want_all: bool) -> tuple[bool, list[ObjectMember]]:
        members = self.get_module_members()
        if want_all:
            if self.__all__ is None:
                # for implicit module members, check __module__ to avoid
                # documenting imported objects
                return True, list(members.values())
            else:
                for member in members.values():
                    if member.__name__ not in self.__all__:
                        member.skipped = True

                return False, list(members.values())
        else:
            memberlist = self.options.members or []
            ret = []
            for name in memberlist:
                if name in members:
                    ret.append(members[name])
                else:
                    logger.warning(__('missing attribute mentioned in :members: option: '
                                      'module %s, attribute %s') %
                                   (safe_getattr(self.object, '__name__', '???'), name),
                                   type='autodoc')
            return False, ret

    def sort_members(self, documenters: list[tuple[Documenter, bool]],
                     order: str) -> list[tuple[Documenter, bool]]:
        if order == 'bysource' and self.__all__:
            assert self.__all__ is not None
            module_all = self.__all__
            module_all_set = set(module_all)
            module_all_len = len(module_all)

            # Sort alphabetically first (for members not listed on the __all__)
            documenters.sort(key=lambda e: e[0].name)

            # Sort by __all__
            def keyfunc(entry: tuple[Documenter, bool]) -> int:
                name = entry[0].name.split('::')[1]
                if name in module_all_set:
                    return module_all.index(name)
                else:
                    return module_all_len
            documenters.sort(key=keyfunc)

            return documenters
        else:
            return super().sort_members(documenters, order)


class ModuleLevelDocumenter(Documenter):
    """
    Specialized Documenter subclass for objects on module level (functions,
    classes, data/constants).
    """
    def resolve_name(self, modname: str | None, parents: Any, path: str, base: str,
                     ) -> tuple[str | None, list[str]]:
        if modname is not None:
            return modname, parents + [base]
        if path:
            modname = path.rstrip('.')
            return modname, parents + [base]

        # if documenting a toplevel object without explicit module,
        # it can be contained in another auto directive ...
        modname = self.env.temp_data.get('autodoc:module')
        # ... or in the scope of a module directive
        if not modname:
            modname = self.env.ref_context.get('py:module')
        # ... else, it stays None, which means invalid
        return modname, parents + [base]


class ClassLevelDocumenter(Documenter):
    """
    Specialized Documenter subclass for objects on class level (methods,
    attributes).
    """
    def resolve_name(self, modname: str | None, parents: Any, path: str, base: str,
                     ) -> tuple[str | None, list[str]]:
        if modname is not None:
            return modname, parents + [base]

        if path:
            mod_cls = path.rstrip('.')
        else:
            # if documenting a class-level object without path,
            # there must be a current class, either from a parent
            # auto directive ...
            mod_cls_ = self.env.temp_data.get('autodoc:class')
            # ... or from a class directive
            if mod_cls_ is None:
                mod_cls_ = self.env.ref_context.get('py:class')
                # ... if still None, there's no way to know
                if mod_cls_ is None:
                    return None, []
            mod_cls = mod_cls_
        modname, sep, cls = mod_cls.rpartition('.')
        parents = [cls]
        # if the module name is still missing, get it like above
        if not modname:
            modname = self.env.temp_data.get('autodoc:module')
        if not modname:
            modname = self.env.ref_context.get('py:module')
        # ... else, it stays None, which means invalid
        return modname, parents + [base]


class DocstringSignatureMixin:
    """
    Mixin for FunctionDocumenter and MethodDocumenter to provide the
    feature of reading the signature from the docstring.
    """
    _new_docstrings: list[list[str]] | None = None
    _signatures: list[str] = []

    def _find_signature(self) -> tuple[str | None, str | None] | None:
        # candidates of the object name
        valid_names = [self.objpath[-1]]  # type: ignore[attr-defined]
        if isinstance(self, ClassDocumenter):
            valid_names.append('__init__')
            if hasattr(self.object, '__mro__'):
                valid_names.extend(cls.__name__ for cls in self.object.__mro__)

        docstrings = self.get_doc()
        if docstrings is None:
            return None, None
        self._new_docstrings = docstrings[:]
        self._signatures = []
        result = None
        for i, doclines in enumerate(docstrings):
            for j, line in enumerate(doclines):
                if not line:
                    # no lines in docstring, no match
                    break

                if line.endswith('\\'):
                    line = line.rstrip('\\').rstrip()

                # match first line of docstring against signature RE
                match = py_ext_sig_re.match(line)
                if not match:
                    break
                exmod, path, base, tp_list, args, retann = match.groups()

                # the base name must match ours
                if base not in valid_names:
                    break

                # re-prepare docstring to ignore more leading indentation
                directive = self.directive  # type: ignore[attr-defined]
                tab_width = directive.state.document.settings.tab_width
                self._new_docstrings[i] = prepare_docstring('\n'.join(doclines[j + 1:]),
                                                            tab_width)

                if result is None:
                    # first signature
                    result = args, retann
                else:
                    # subsequent signatures
                    self._signatures.append(f"({args}) -> {retann}")

            if result is not None:
                # finish the loop when signature found
                break

        return result

    def get_doc(self) -> list[list[str]] | None:
        if self._new_docstrings is not None:
            return self._new_docstrings
        return super().get_doc()  # type: ignore[misc]

    def format_signature(self, **kwargs: Any) -> str:
        self.args: str | None
        if (self.args is None
                and self.config.autodoc_docstring_signature):  # type: ignore[attr-defined]
            # only act if a signature is not explicitly given already, and if
            # the feature is enabled
            result = self._find_signature()
            if result is not None:
                self.args, self.retann = result
        sig = super().format_signature(**kwargs)  # type: ignore[misc]
        if self._signatures:
            return "\n".join([sig] + self._signatures)
        else:
            return sig


class DocstringStripSignatureMixin(DocstringSignatureMixin):
    """
    Mixin for AttributeDocumenter to provide the
    feature of stripping any function signature from the docstring.
    """
    def format_signature(self, **kwargs: Any) -> str:
        if (
            self.args is None
            and self.config.autodoc_docstring_signature  # type: ignore[attr-defined]
        ):
            # only act if a signature is not explicitly given already, and if
            # the feature is enabled
            result = self._find_signature()
            if result is not None:
                # Discarding _args is a only difference with
                # DocstringSignatureMixin.format_signature.
                # Documenter.format_signature use self.args value to format.
                _args, self.retann = result
        return super().format_signature(**kwargs)


class FunctionDocumenter(DocstringSignatureMixin, ModuleLevelDocumenter):  # type: ignore[misc]
    """
    Specialized Documenter subclass for functions.
    """
    objtype = 'function'
    member_order = 30

    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any,
                            ) -> bool:
        # supports functions, builtins and bound methods exported at the module level
        return (inspect.isfunction(member) or inspect.isbuiltin(member) or
                (inspect.isroutine(member) and isinstance(parent, ModuleDocumenter)))

    def format_args(self, **kwargs: Any) -> str:
        if self.config.autodoc_typehints in ('none', 'description'):
            kwargs.setdefault('show_annotation', False)
        if self.config.autodoc_typehints_format == "short":
            kwargs.setdefault('unqualified_typehints', True)

        try:
            self.env.app.emit('autodoc-before-process-signature', self.object, False)
            sig = inspect.signature(self.object, type_aliases=self.config.autodoc_type_aliases)
            args = stringify_signature(sig, **kwargs)
        except TypeError as exc:
            logger.warning(__("Failed to get a function signature for %s: %s"),
                           self.fullname, exc)
            return ''
        except ValueError:
            args = ''

        if self.config.strip_signature_backslash:
            # escape backslashes for reST
            args = args.replace('\\', '\\\\')
        return args

    def document_members(self, all_members: bool = False) -> None:
        pass

    def add_directive_header(self, sig: str) -> None:
        sourcename = self.get_sourcename()
        super().add_directive_header(sig)

        if inspect.iscoroutinefunction(self.object) or inspect.isasyncgenfunction(self.object):
            self.add_line('   :async:', sourcename)

    def format_signature(self, **kwargs: Any) -> str:
        if self.config.autodoc_typehints_format == "short":
            kwargs.setdefault('unqualified_typehints', True)

        sigs = []
        if (self.analyzer and
                '.'.join(self.objpath) in self.analyzer.overloads and
                self.config.autodoc_typehints != 'none'):
            # Use signatures for overloaded functions instead of the implementation function.
            overloaded = True
        else:
            overloaded = False
            sig = super().format_signature(**kwargs)
            sigs.append(sig)

        if inspect.is_singledispatch_function(self.object):
            # append signature of singledispatch'ed functions
            for typ, func in self.object.registry.items():
                if typ is object:
                    pass  # default implementation. skipped.
                else:
                    dispatchfunc = self.annotate_to_first_argument(func, typ)
                    if dispatchfunc:
                        documenter = FunctionDocumenter(self.directive, '')
                        documenter.object = dispatchfunc
                        documenter.objpath = ['']
                        sigs.append(documenter.format_signature())
        if overloaded and self.analyzer is not None:
            actual = inspect.signature(self.object,
                                       type_aliases=self.config.autodoc_type_aliases)
            __globals__ = safe_getattr(self.object, '__globals__', {})
            for overload in self.analyzer.overloads['.'.join(self.objpath)]:
                overload = self.merge_default_value(actual, overload)
                overload = evaluate_signature(overload, __globals__,
                                              self.config.autodoc_type_aliases)

                sig = stringify_signature(overload, **kwargs)
                sigs.append(sig)

        return "\n".join(sigs)

    def merge_default_value(self, actual: Signature, overload: Signature) -> Signature:
        """Merge default values of actual implementation to the overload variants."""
        parameters = list(overload.parameters.values())
        for i, param in enumerate(parameters):
            actual_param = actual.parameters.get(param.name)
            if actual_param and param.default == '...':
                parameters[i] = param.replace(default=actual_param.default)

        return overload.replace(parameters=parameters)

    def annotate_to_first_argument(self, func: Callable, typ: type) -> Callable | None:
        """Annotate type hint to the first argument of function if needed."""
        try:
            sig = inspect.signature(func, type_aliases=self.config.autodoc_type_aliases)
        except TypeError as exc:
            logger.warning(__("Failed to get a function signature for %s: %s"),
                           self.fullname, exc)
            return None
        except ValueError:
            return None

        if len(sig.parameters) == 0:
            return None

        def dummy():
            pass

        params = list(sig.parameters.values())
        if params[0].annotation is Parameter.empty:
            params[0] = params[0].replace(annotation=typ)
            try:
                dummy.__signature__ = sig.replace(  # type: ignore[attr-defined]
                    parameters=params)
                return dummy
            except (AttributeError, TypeError):
                # failed to update signature (ex. built-in or extension types)
                return None

        return func


class DecoratorDocumenter(FunctionDocumenter):
    """
    Specialized Documenter subclass for decorator functions.
    """
    objtype = 'decorator'

    # must be lower than FunctionDocumenter
    priority = -1

    def format_args(self, **kwargs: Any) -> str:
        args = super().format_args(**kwargs)
        if ',' in args:
            return args
        else:
            return ''


# Types which have confusing metaclass signatures it would be best not to show.
# These are listed by name, rather than storing the objects themselves, to avoid
# needing to import the modules.
_METACLASS_CALL_BLACKLIST = [
    'enum.EnumMeta.__call__',
]


# Types whose __new__ signature is a pass-through.
_CLASS_NEW_BLACKLIST = [
    'typing.Generic.__new__',
]


class ClassDocumenter(DocstringSignatureMixin, ModuleLevelDocumenter):  # type: ignore[misc]
    """
    Specialized Documenter subclass for classes.
    """
    objtype = 'class'
    member_order = 20
    option_spec: OptionSpec = {
        'members': members_option, 'undoc-members': bool_option,
        'no-index': bool_option, 'inherited-members': inherited_members_option,
        'show-inheritance': bool_option, 'member-order': member_order_option,
        'exclude-members': exclude_members_option,
        'private-members': members_option, 'special-members': members_option,
        'class-doc-from': class_doc_from_option,
        'noindex': bool_option,
    }

    # Must be higher than FunctionDocumenter, ClassDocumenter, and
    # AttributeDocumenter as NewType can be an attribute and is a class
    # after Python 3.10. Before 3.10 it is a kind of function object
    priority = 15

    _signature_class: Any = None
    _signature_method_name: str = ''

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)

        if self.config.autodoc_class_signature == 'separated':
            self.options = self.options.copy()

            # show __init__() method
            if self.options.special_members is None:
                self.options['special-members'] = ['__new__', '__init__']
            else:
                self.options.special_members.append('__new__')
                self.options.special_members.append('__init__')

        merge_members_option(self.options)

    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any,
                            ) -> bool:
        return isinstance(member, type) or (
            isattr and (inspect.isNewType(member) or isinstance(member, TypeVar)))

    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror)
        # if the class is documented under another name, document it
        # as data/attribute
        if ret:
            if hasattr(self.object, '__name__'):
                self.doc_as_attr = (self.objpath[-1] != self.object.__name__)
            else:
                self.doc_as_attr = True
            if inspect.isNewType(self.object) or isinstance(self.object, TypeVar):
                modname = getattr(self.object, '__module__', self.modname)
                if modname != self.modname and self.modname.startswith(modname):
                    bases = self.modname[len(modname):].strip('.').split('.')
                    self.objpath = bases + self.objpath
                    self.modname = modname
        return ret

    def _get_signature(self) -> tuple[Any | None, str | None, Signature | None]:
        if inspect.isNewType(self.object) or isinstance(self.object, TypeVar):
            # Suppress signature
            return None, None, None

        def get_user_defined_function_or_method(obj: Any, attr: str) -> Any:
            """ Get the `attr` function or method from `obj`, if it is user-defined. """
            if inspect.is_builtin_class_method(obj, attr):
                return None
            attr = self.get_attr(obj, attr, None)
            if not (inspect.ismethod(attr) or inspect.isfunction(attr)):
                return None
            return attr

        # This sequence is copied from inspect._signature_from_callable.
        # ValueError means that no signature could be found, so we keep going.

        # First, we check the obj has a __signature__ attribute
        if (hasattr(self.object, '__signature__') and
                isinstance(self.object.__signature__, Signature)):
            return None, None, self.object.__signature__

        # Next, let's see if it has an overloaded __call__ defined
        # in its metaclass
        call = get_user_defined_function_or_method(type(self.object), '__call__')

        if call is not None:
            if f"{call.__module__}.{call.__qualname__}" in _METACLASS_CALL_BLACKLIST:
                call = None

        if call is not None:
            self.env.app.emit('autodoc-before-process-signature', call, True)
            try:
                sig = inspect.signature(call, bound_method=True,
                                        type_aliases=self.config.autodoc_type_aliases)
                return type(self.object), '__call__', sig
            except ValueError:
                pass

        # Now we check if the 'obj' class has a '__new__' method
        new = get_user_defined_function_or_method(self.object, '__new__')

        if new is not None:
            if f"{new.__module__}.{new.__qualname__}" in _CLASS_NEW_BLACKLIST:
                new = None

        if new is not None:
            self.env.app.emit('autodoc-before-process-signature', new, True)
            try:
                sig = inspect.signature(new, bound_method=True,
                                        type_aliases=self.config.autodoc_type_aliases)
                return self.object, '__new__', sig
            except ValueError:
                pass

        # Finally, we should have at least __init__ implemented
        init = get_user_defined_function_or_method(self.object, '__init__')
        if init is not None:
            self.env.app.emit('autodoc-before-process-signature', init, True)
            try:
                sig = inspect.signature(init, bound_method=True,
                                        type_aliases=self.config.autodoc_type_aliases)
                return self.object, '__init__', sig
            except ValueError:
                pass

        # None of the attributes are user-defined, so fall back to let inspect
        # handle it.
        # We don't know the exact method that inspect.signature will read
        # the signature from, so just pass the object itself to our hook.
        self.env.app.emit('autodoc-before-process-signature', self.object, False)
        try:
            sig = inspect.signature(self.object, bound_method=False,
                                    type_aliases=self.config.autodoc_type_aliases)
            return None, None, sig
        except ValueError:
            pass

        # Still no signature: happens e.g. for old-style classes
        # with __init__ in C and no `__text_signature__`.
        return None, None, None

    def format_args(self, **kwargs: Any) -> str:
        if self.config.autodoc_typehints in ('none', 'description'):
            kwargs.setdefault('show_annotation', False)
        if self.config.autodoc_typehints_format == "short":
            kwargs.setdefault('unqualified_typehints', True)

        try:
            self._signature_class, _signature_method_name, sig = self._get_signature()
        except TypeError as exc:
            # __signature__ attribute contained junk
            logger.warning(__("Failed to get a constructor signature for %s: %s"),
                           self.fullname, exc)
            return ''
        self._signature_method_name = _signature_method_name or ''

        if sig is None:
            return ''

        return stringify_signature(sig, show_return_annotation=False, **kwargs)

    def _find_signature(self) -> tuple[str | None, str | None] | None:
        result = super()._find_signature()
        if result is not None:
            # Strip a return value from signature of constructor in docstring (first entry)
            result = (result[0], None)

        for i, sig in enumerate(self._signatures):
            if sig.endswith(' -> None'):
                # Strip a return value from signatures of constructor in docstring (subsequent
                # entries)
                self._signatures[i] = sig[:-8]

        return result

    def format_signature(self, **kwargs: Any) -> str:
        if self.doc_as_attr:
            return ''
        if self.config.autodoc_class_signature == 'separated':
            # do not show signatures
            return ''

        if self.config.autodoc_typehints_format == "short":
            kwargs.setdefault('unqualified_typehints', True)

        sig = super().format_signature()
        sigs = []

        overloads = self.get_overloaded_signatures()
        if overloads and self.config.autodoc_typehints != 'none':
            # Use signatures for overloaded methods instead of the implementation method.
            method = safe_getattr(self._signature_class, self._signature_method_name, None)
            __globals__ = safe_getattr(method, '__globals__', {})
            for overload in overloads:
                overload = evaluate_signature(overload, __globals__,
                                              self.config.autodoc_type_aliases)

                parameters = list(overload.parameters.values())
                overload = overload.replace(parameters=parameters[1:],
                                            return_annotation=Parameter.empty)
                sig = stringify_signature(overload, **kwargs)
                sigs.append(sig)
        else:
            sigs.append(sig)

        return "\n".join(sigs)

    def get_overloaded_signatures(self) -> list[Signature]:
        if self._signature_class and self._signature_method_name:
            for cls in self._signature_class.__mro__:
                try:
                    analyzer = ModuleAnalyzer.for_module(cls.__module__)
                    analyzer.analyze()
                    qualname = '.'.join([cls.__qualname__, self._signature_method_name])
                    if qualname in analyzer.overloads:
                        return analyzer.overloads.get(qualname, [])
                    elif qualname in analyzer.tagorder:
                        # the constructor is defined in the class, but not overridden.
                        return []
                except PycodeError:
                    pass

        return []

    def get_canonical_fullname(self) -> str | None:
        __modname__ = safe_getattr(self.object, '__module__', self.modname)
        __qualname__ = safe_getattr(self.object, '__qualname__', None)
        if __qualname__ is None:
            __qualname__ = safe_getattr(self.object, '__name__', None)
        if __qualname__ and '<locals>' in __qualname__:
            # No valid qualname found if the object is defined as locals
            __qualname__ = None

        if __modname__ and __qualname__:
            return '.'.join([__modname__, __qualname__])
        else:
            return None

    def add_directive_header(self, sig: str) -> None:
        sourcename = self.get_sourcename()

        if self.doc_as_attr:
            self.directivetype = 'attribute'
        super().add_directive_header(sig)

        if inspect.isNewType(self.object) or isinstance(self.object, TypeVar):
            return

        if self.analyzer and '.'.join(self.objpath) in self.analyzer.finals:
            self.add_line('   :final:', sourcename)

        canonical_fullname = self.get_canonical_fullname()
        if (not self.doc_as_attr and not inspect.isNewType(self.object)
                and canonical_fullname and self.fullname != canonical_fullname):
            self.add_line('   :canonical: %s' % canonical_fullname, sourcename)

        # add inheritance info, if wanted
        if not self.doc_as_attr and self.options.show_inheritance:
            if inspect.getorigbases(self.object):
                # A subclass of generic types
                # refs: PEP-560 <https://peps.python.org/pep-0560/>
                bases = list(self.object.__orig_bases__)
            elif hasattr(self.object, '__bases__') and len(self.object.__bases__):
                # A normal class
                bases = list(self.object.__bases__)
            else:
                bases = []

            self.env.events.emit('autodoc-process-bases',
                                 self.fullname, self.object, self.options, bases)

            if self.config.autodoc_typehints_format == "short":
                base_classes = [restify(cls, "smart") for cls in bases]
            else:
                base_classes = [restify(cls) for cls in bases]

            sourcename = self.get_sourcename()
            self.add_line('', sourcename)
            self.add_line('   ' + _('Bases: %s') % ', '.join(base_classes), sourcename)

    def get_object_members(self, want_all: bool) -> tuple[bool, list[ObjectMember]]:
        members = get_class_members(self.object, self.objpath, self.get_attr,
                                    self.config.autodoc_inherit_docstrings)
        if not want_all:
            if not self.options.members:
                return False, []
            # specific members given
            selected = []
            for name in self.options.members:
                if name in members:
                    selected.append(members[name])
                else:
                    logger.warning(__('missing attribute %s in object %s') %
                                   (name, self.fullname), type='autodoc')
            return False, selected
        elif self.options.inherited_members:
            return False, list(members.values())
        else:
            return False, [m for m in members.values() if m.class_ == self.object]

    def get_doc(self) -> list[list[str]] | None:
        if isinstance(self.object, TypeVar):
            if self.object.__doc__ == TypeVar.__doc__:
                return []
        if sys.version_info[:2] < (3, 10):
            if inspect.isNewType(self.object) or isinstance(self.object, TypeVar):
                parts = self.modname.strip('.').split('.')
                orig_objpath = self.objpath
                for i in range(len(parts)):
                    new_modname = '.'.join(parts[:len(parts) - i])
                    new_objpath = parts[len(parts) - i:] + orig_objpath
                    try:
                        analyzer = ModuleAnalyzer.for_module(new_modname)
                        analyzer.analyze()
                        key = ('', new_objpath[-1])
                        comment = list(analyzer.attr_docs.get(key, []))
                        if comment:
                            self.objpath = new_objpath
                            self.modname = new_modname
                            return [comment]
                    except PycodeError:
                        pass
        if self.doc_as_attr:
            # Don't show the docstring of the class when it is an alias.
            if self.get_variable_comment():
                return []
            else:
                return None

        lines = getattr(self, '_new_docstrings', None)
        if lines is not None:
            return lines

        classdoc_from = self.options.get('class-doc-from', self.config.autoclass_content)

        docstrings = []
        attrdocstring = getdoc(self.object, self.get_attr)
        if attrdocstring:
            docstrings.append(attrdocstring)

        # for classes, what the "docstring" is can be controlled via a
        # config value; the default is only the class docstring
        if classdoc_from in ('both', 'init'):
            __init__ = self.get_attr(self.object, '__init__', None)
            initdocstring = getdoc(__init__, self.get_attr,
                                   self.config.autodoc_inherit_docstrings,
                                   self.object, '__init__')
            # for new-style classes, no __init__ means default __init__
            if (initdocstring is not None and
                (initdocstring == object.__init__.__doc__ or  # for pypy
                 initdocstring.strip() == object.__init__.__doc__)):  # for !pypy
                initdocstring = None
            if not initdocstring:
                # try __new__
                __new__ = self.get_attr(self.object, '__new__', None)
                initdocstring = getdoc(__new__, self.get_attr,
                                       self.config.autodoc_inherit_docstrings,
                                       self.object, '__new__')
                # for new-style classes, no __new__ means default __new__
                if (initdocstring is not None and
                    (initdocstring == object.__new__.__doc__ or  # for pypy
                     initdocstring.strip() == object.__new__.__doc__)):  # for !pypy
                    initdocstring = None
            if initdocstring:
                if classdoc_from == 'init':
                    docstrings = [initdocstring]
                else:
                    docstrings.append(initdocstring)

        tab_width = self.directive.state.document.settings.tab_width
        return [prepare_docstring(docstring, tab_width) for docstring in docstrings]

    def get_variable_comment(self) -> list[str] | None:
        try:
            key = ('', '.'.join(self.objpath))
            if self.doc_as_attr:
                analyzer = ModuleAnalyzer.for_module(self.modname)
            else:
                analyzer = ModuleAnalyzer.for_module(self.get_real_modname())
            analyzer.analyze()
            return list(analyzer.attr_docs.get(key, []))
        except PycodeError:
            return None

    def add_content(self, more_content: StringList | None) -> None:
        if inspect.isNewType(self.object):
            if self.config.autodoc_typehints_format == "short":
                supertype = restify(self.object.__supertype__, "smart")
            else:
                supertype = restify(self.object.__supertype__)

            more_content = StringList([_('alias of %s') % supertype, ''], source='')
        if isinstance(self.object, TypeVar):
            attrs = [repr(self.object.__name__)]
            for constraint in self.object.__constraints__:
                if self.config.autodoc_typehints_format == "short":
                    attrs.append(stringify_annotation(constraint, "smart"))
                else:
                    attrs.append(stringify_annotation(constraint))
            if self.object.__bound__:
                if self.config.autodoc_typehints_format == "short":
                    bound = restify(self.object.__bound__, "smart")
                else:
                    bound = restify(self.object.__bound__)
                attrs.append(r"bound=\ " + bound)
            if self.object.__covariant__:
                attrs.append("covariant=True")
            if self.object.__contravariant__:
                attrs.append("contravariant=True")

            more_content = StringList(
                [_('alias of TypeVar(%s)') % ", ".join(attrs), ''],
                source='',
            )
        if self.doc_as_attr and self.modname != self.get_real_modname():
            try:
                # override analyzer to obtain doccomment around its definition.
                self.analyzer = ModuleAnalyzer.for_module(self.modname)
                self.analyzer.analyze()
            except PycodeError:
                pass

        if self.doc_as_attr and not self.get_variable_comment():
            try:
                if self.config.autodoc_typehints_format == "short":
                    alias = restify(self.object, "smart")
                else:
                    alias = restify(self.object)
                more_content = StringList([_('alias of %s') % alias], source='')
            except AttributeError:
                pass  # Invalid class object is passed.

        super().add_content(more_content)

    def document_members(self, all_members: bool = False) -> None:
        if self.doc_as_attr:
            return
        super().document_members(all_members)

    def generate(
        self,
        more_content: StringList | None = None,
        real_modname: str | None = None,
        check_module: bool = False,
        all_members: bool = False,
    ) -> None:
        # Do not pass real_modname and use the name from the __module__
        # attribute of the class.
        # If a class gets imported into the module real_modname
        # the analyzer won't find the source of the class, if
        # it looks in real_modname.
        return super().generate(more_content=more_content,
                                check_module=check_module,
                                all_members=all_members)


class ExceptionDocumenter(ClassDocumenter):
    """
    Specialized ClassDocumenter subclass for exceptions.
    """
    objtype = 'exception'
    member_order = 10

    # needs a higher priority than ClassDocumenter
    priority = ClassDocumenter.priority + 5

    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any,
                            ) -> bool:
        try:
            return isinstance(member, type) and issubclass(member, BaseException)
        except TypeError as exc:
            # It's possible for a member to be considered a type, but fail
            # issubclass checks due to not being a class. For example:
            # https://github.com/sphinx-doc/sphinx/issues/11654#issuecomment-1696790436
            msg = (
                f'{cls.__name__} failed to discern if member {member} with'
                f' membername {membername} is a BaseException subclass.'
            )
            raise ValueError(msg) from exc


class DataDocumenterMixinBase:
    # define types of instance variables
    config: Config
    env: BuildEnvironment
    modname: str
    parent: Any
    object: Any
    objpath: list[str]

    def should_suppress_directive_header(self) -> bool:
        """Check directive header should be suppressed."""
        return False

    def should_suppress_value_header(self) -> bool:
        """Check :value: header should be suppressed."""
        return False

    def update_content(self, more_content: StringList) -> None:
        """Update docstring, for example with TypeVar variance."""
        pass


class GenericAliasMixin(DataDocumenterMixinBase):
    """
    Mixin for DataDocumenter and AttributeDocumenter to provide the feature for
    supporting GenericAliases.
    """

    def should_suppress_directive_header(self) -> bool:
        return (inspect.isgenericalias(self.object) or
                super().should_suppress_directive_header())

    def update_content(self, more_content: StringList) -> None:
        if inspect.isgenericalias(self.object):
            if self.config.autodoc_typehints_format == "short":
                alias = restify(self.object, "smart")
            else:
                alias = restify(self.object)

            more_content.append(_('alias of %s') % alias, '')
            more_content.append('', '')

        super().update_content(more_content)


class UninitializedGlobalVariableMixin(DataDocumenterMixinBase):
    """
    Mixin for DataDocumenter to provide the feature for supporting uninitialized
    (type annotation only) global variables.
    """

    def import_object(self, raiseerror: bool = False) -> bool:
        try:
            return super().import_object(raiseerror=True)  # type: ignore[misc]
        except ImportError as exc:
            # annotation only instance variable (PEP-526)
            try:
                with mock(self.config.autodoc_mock_imports):
                    parent = import_module(self.modname, self.config.autodoc_warningiserror)
                    annotations = get_type_hints(parent, None,
                                                 self.config.autodoc_type_aliases)
                    if self.objpath[-1] in annotations:
                        self.object = UNINITIALIZED_ATTR
                        self.parent = parent
                        return True
            except ImportError:
                pass

            if raiseerror:
                raise
            logger.warning(exc.args[0], type='autodoc', subtype='import_object')
            self.env.note_reread()
            return False

    def should_suppress_value_header(self) -> bool:
        return (self.object is UNINITIALIZED_ATTR or
                super().should_suppress_value_header())

    def get_doc(self) -> list[list[str]] | None:
        if self.object is UNINITIALIZED_ATTR:
            return []
        else:
            return super().get_doc()  # type: ignore[misc]


class DataDocumenter(GenericAliasMixin,
                     UninitializedGlobalVariableMixin, ModuleLevelDocumenter):
    """
    Specialized Documenter subclass for data items.
    """
    objtype = 'data'
    member_order = 40
    priority = -10
    option_spec: OptionSpec = dict(ModuleLevelDocumenter.option_spec)
    option_spec["annotation"] = annotation_option
    option_spec["no-value"] = bool_option

    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any,
                            ) -> bool:
        return isinstance(parent, ModuleDocumenter) and isattr

    def update_annotations(self, parent: Any) -> None:
        """Update __annotations__ to support type_comment and so on."""
        annotations = dict(inspect.getannotations(parent))
        parent.__annotations__ = annotations

        try:
            analyzer = ModuleAnalyzer.for_module(self.modname)
            analyzer.analyze()
            for (classname, attrname), annotation in analyzer.annotations.items():
                if classname == '' and attrname not in annotations:
                    annotations[attrname] = annotation
        except PycodeError:
            pass

    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror)
        if self.parent:
            self.update_annotations(self.parent)

        return ret

    def should_suppress_value_header(self) -> bool:
        if super().should_suppress_value_header():
            return True
        else:
            doc = self.get_doc() or []
            docstring, metadata = separate_metadata('\n'.join(sum(doc, [])))
            if 'hide-value' in metadata:
                return True

        return False

    def add_directive_header(self, sig: str) -> None:
        super().add_directive_header(sig)
        sourcename = self.get_sourcename()
        if self.options.annotation is SUPPRESS or self.should_suppress_directive_header():
            pass
        elif self.options.annotation:
            self.add_line('   :annotation: %s' % self.options.annotation,
                          sourcename)
        else:
            if self.config.autodoc_typehints != 'none':
                # obtain annotation for this data
                annotations = get_type_hints(self.parent, None,
                                             self.config.autodoc_type_aliases)
                if self.objpath[-1] in annotations:
                    if self.config.autodoc_typehints_format == "short":
                        objrepr = stringify_annotation(annotations.get(self.objpath[-1]),
                                                       "smart")
                    else:
                        objrepr = stringify_annotation(annotations.get(self.objpath[-1]),
                                                       "fully-qualified-except-typing")
                    self.add_line('   :type: ' + objrepr, sourcename)

            try:
                if (self.options.no_value or self.should_suppress_value_header() or
                        ismock(self.object)):
                    pass
                else:
                    objrepr = object_description(self.object)
                    self.add_line('   :value: ' + objrepr, sourcename)
            except ValueError:
                pass

    def document_members(self, all_members: bool = False) -> None:
        pass

    def get_real_modname(self) -> str:
        real_modname = self.get_attr(self.parent or self.object, '__module__', None)
        return real_modname or self.modname

    def get_module_comment(self, attrname: str) -> list[str] | None:
        try:
            analyzer = ModuleAnalyzer.for_module(self.modname)
            analyzer.analyze()
            key = ('', attrname)
            if key in analyzer.attr_docs:
                return list(analyzer.attr_docs[key])
        except PycodeError:
            pass

        return None

    def get_doc(self) -> list[list[str]] | None:
        # Check the variable has a docstring-comment
        comment = self.get_module_comment(self.objpath[-1])
        if comment:
            return [comment]
        else:
            return super().get_doc()

    def add_content(self, more_content: StringList | None) -> None:
        # Disable analyzing variable comment on Documenter.add_content() to control it on
        # DataDocumenter.add_content()
        self.analyzer = None

        if not more_content:
            more_content = StringList()

        self.update_content(more_content)
        super().add_content(more_content)


class MethodDocumenter(DocstringSignatureMixin, ClassLevelDocumenter):  # type: ignore[misc]
    """
    Specialized Documenter subclass for methods (normal, static and class).
    """
    objtype = 'method'
    directivetype = 'method'
    member_order = 50
    priority = 1  # must be more than FunctionDocumenter

    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any,
                            ) -> bool:
        return inspect.isroutine(member) and not isinstance(parent, ModuleDocumenter)

    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror)
        if not ret:
            return ret

        # to distinguish classmethod/staticmethod
        obj = self.parent.__dict__.get(self.object_name)
        if obj is None:
            obj = self.object

        if (inspect.isclassmethod(obj) or
                inspect.isstaticmethod(obj, cls=self.parent, name=self.object_name)):
            # document class and static members before ordinary ones
            self.member_order = self.member_order - 1

        return ret

    def format_args(self, **kwargs: Any) -> str:
        if self.config.autodoc_typehints in ('none', 'description'):
            kwargs.setdefault('show_annotation', False)
        if self.config.autodoc_typehints_format == "short":
            kwargs.setdefault('unqualified_typehints', True)

        try:
            if self.object == object.__init__ and self.parent != object:
                # Classes not having own __init__() method are shown as no arguments.
                #
                # Note: The signature of object.__init__() is (self, /, *args, **kwargs).
                #       But it makes users confused.
                args = '()'
            else:
                if inspect.isstaticmethod(self.object, cls=self.parent, name=self.object_name):
                    self.env.app.emit('autodoc-before-process-signature', self.object, False)
                    sig = inspect.signature(self.object, bound_method=False,
                                            type_aliases=self.config.autodoc_type_aliases)
                else:
                    self.env.app.emit('autodoc-before-process-signature', self.object, True)
                    sig = inspect.signature(self.object, bound_method=True,
                                            type_aliases=self.config.autodoc_type_aliases)
                args = stringify_signature(sig, **kwargs)
        except TypeError as exc:
            logger.warning(__("Failed to get a method signature for %s: %s"),
                           self.fullname, exc)
            return ''
        except ValueError:
            args = ''

        if self.config.strip_signature_backslash:
            # escape backslashes for reST
            args = args.replace('\\', '\\\\')
        return args

    def add_directive_header(self, sig: str) -> None:
        super().add_directive_header(sig)

        sourcename = self.get_sourcename()
        obj = self.parent.__dict__.get(self.object_name, self.object)
        if inspect.isabstractmethod(obj):
            self.add_line('   :abstractmethod:', sourcename)
        if inspect.iscoroutinefunction(obj) or inspect.isasyncgenfunction(obj):
            self.add_line('   :async:', sourcename)
        if inspect.isclassmethod(obj):
            self.add_line('   :classmethod:', sourcename)
        if inspect.isstaticmethod(obj, cls=self.parent, name=self.object_name):
            self.add_line('   :staticmethod:', sourcename)
        if self.analyzer and '.'.join(self.objpath) in self.analyzer.finals:
            self.add_line('   :final:', sourcename)

    def document_members(self, all_members: bool = False) -> None:
        pass

    def format_signature(self, **kwargs: Any) -> str:
        if self.config.autodoc_typehints_format == "short":
            kwargs.setdefault('unqualified_typehints', True)

        sigs = []
        if (self.analyzer and
                '.'.join(self.objpath) in self.analyzer.overloads and
                self.config.autodoc_typehints != 'none'):
            # Use signatures for overloaded methods instead of the implementation method.
            overloaded = True
        else:
            overloaded = False
            sig = super().format_signature(**kwargs)
            sigs.append(sig)

        meth = self.parent.__dict__.get(self.objpath[-1])
        if inspect.is_singledispatch_method(meth):
            # append signature of singledispatch'ed functions
            for typ, func in meth.dispatcher.registry.items():
                if typ is object:
                    pass  # default implementation. skipped.
                else:
                    dispatchmeth = self.annotate_to_first_argument(func, typ)
                    if dispatchmeth:
                        documenter = MethodDocumenter(self.directive, '')
                        documenter.parent = self.parent
                        documenter.object = dispatchmeth
                        documenter.objpath = ['']
                        sigs.append(documenter.format_signature())
        if overloaded and self.analyzer is not None:
            if inspect.isstaticmethod(self.object, cls=self.parent, name=self.object_name):
                actual = inspect.signature(self.object, bound_method=False,
                                           type_aliases=self.config.autodoc_type_aliases)
            else:
                actual = inspect.signature(self.object, bound_method=True,
                                           type_aliases=self.config.autodoc_type_aliases)

            __globals__ = safe_getattr(self.object, '__globals__', {})
            for overload in self.analyzer.overloads['.'.join(self.objpath)]:
                overload = self.merge_default_value(actual, overload)
                overload = evaluate_signature(overload, __globals__,
                                              self.config.autodoc_type_aliases)

                if not inspect.isstaticmethod(self.object, cls=self.parent,
                                              name=self.object_name):
                    parameters = list(overload.parameters.values())
                    overload = overload.replace(parameters=parameters[1:])
                sig = stringify_signature(overload, **kwargs)
                sigs.append(sig)

        return "\n".join(sigs)

    def merge_default_value(self, actual: Signature, overload: Signature) -> Signature:
        """Merge default values of actual implementation to the overload variants."""
        parameters = list(overload.parameters.values())
        for i, param in enumerate(parameters):
            actual_param = actual.parameters.get(param.name)
            if actual_param and param.default == '...':
                parameters[i] = param.replace(default=actual_param.default)

        return overload.replace(parameters=parameters)

    def annotate_to_first_argument(self, func: Callable, typ: type) -> Callable | None:
        """Annotate type hint to the first argument of function if needed."""
        try:
            sig = inspect.signature(func, type_aliases=self.config.autodoc_type_aliases)
        except TypeError as exc:
            logger.warning(__("Failed to get a method signature for %s: %s"),
                           self.fullname, exc)
            return None
        except ValueError:
            return None

        if len(sig.parameters) == 1:
            return None

        def dummy():
            pass

        params = list(sig.parameters.values())
        if params[1].annotation is Parameter.empty:
            params[1] = params[1].replace(annotation=typ)
            try:
                dummy.__signature__ = sig.replace(  # type: ignore[attr-defined]
                    parameters=params)
                return dummy
            except (AttributeError, TypeError):
                # failed to update signature (ex. built-in or extension types)
                return None

        return func

    def get_doc(self) -> list[list[str]] | None:
        if self._new_docstrings is not None:
            # docstring already returned previously, then modified by
            # `DocstringSignatureMixin`.  Just return the previously-computed
            # result, so that we don't lose the processing done by
            # `DocstringSignatureMixin`.
            return self._new_docstrings
        if self.objpath[-1] == '__init__':
            docstring = getdoc(self.object, self.get_attr,
                               self.config.autodoc_inherit_docstrings,
                               self.parent, self.object_name)
            if (docstring is not None and
                (docstring == object.__init__.__doc__ or  # for pypy
                 docstring.strip() == object.__init__.__doc__)):  # for !pypy
                docstring = None
            if docstring:
                tab_width = self.directive.state.document.settings.tab_width
                return [prepare_docstring(docstring, tabsize=tab_width)]
            else:
                return []
        elif self.objpath[-1] == '__new__':
            docstring = getdoc(self.object, self.get_attr,
                               self.config.autodoc_inherit_docstrings,
                               self.parent, self.object_name)
            if (docstring is not None and
                (docstring == object.__new__.__doc__ or  # for pypy
                 docstring.strip() == object.__new__.__doc__)):  # for !pypy
                docstring = None
            if docstring:
                tab_width = self.directive.state.document.settings.tab_width
                return [prepare_docstring(docstring, tabsize=tab_width)]
            else:
                return []
        else:
            return super().get_doc()


class NonDataDescriptorMixin(DataDocumenterMixinBase):
    """
    Mixin for AttributeDocumenter to provide the feature for supporting non
    data-descriptors.

    .. note:: This mix-in must be inherited after other mix-ins.  Otherwise, docstring
              and :value: header will be suppressed unexpectedly.
    """

    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror)  # type: ignore[misc]
        if ret and not inspect.isattributedescriptor(self.object):
            self.non_data_descriptor = True
        else:
            self.non_data_descriptor = False

        return ret

    def should_suppress_value_header(self) -> bool:
        return (not getattr(self, 'non_data_descriptor', False) or
                super().should_suppress_directive_header())

    def get_doc(self) -> list[list[str]] | None:
        if getattr(self, 'non_data_descriptor', False):
            # the docstring of non datadescriptor is very probably the wrong thing
            # to display
            return None
        else:
            return super().get_doc()  # type: ignore[misc]


class SlotsMixin(DataDocumenterMixinBase):
    """
    Mixin for AttributeDocumenter to provide the feature for supporting __slots__.
    """

    def isslotsattribute(self) -> bool:
        """Check the subject is an attribute in __slots__."""
        try:
            if parent___slots__ := inspect.getslots(self.parent):
                return self.objpath[-1] in parent___slots__
            else:
                return False
        except (ValueError, TypeError):
            return False

    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror)  # type: ignore[misc]
        if self.isslotsattribute():
            self.object = SLOTSATTR

        return ret

    def should_suppress_value_header(self) -> bool:
        if self.object is SLOTSATTR:
            return True
        else:
            return super().should_suppress_value_header()

    def get_doc(self) -> list[list[str]] | None:
        if self.object is SLOTSATTR:
            try:
                parent___slots__ = inspect.getslots(self.parent)
                if parent___slots__ and parent___slots__.get(self.objpath[-1]):
                    docstring = prepare_docstring(parent___slots__[self.objpath[-1]])
                    return [docstring]
                else:
                    return []
            except ValueError as exc:
                logger.warning(__('Invalid __slots__ found on %s. Ignored.'),
                               (self.parent.__qualname__, exc), type='autodoc')
                return []
        else:
            return super().get_doc()  # type: ignore[misc]


class RuntimeInstanceAttributeMixin(DataDocumenterMixinBase):
    """
    Mixin for AttributeDocumenter to provide the feature for supporting runtime
    instance attributes (that are defined in __init__() methods with doc-comments).

    Example:

        class Foo:
            def __init__(self):
                self.attr = None  #: This is a target of this mix-in.
    """

    RUNTIME_INSTANCE_ATTRIBUTE = object()

    def is_runtime_instance_attribute(self, parent: Any) -> bool:
        """Check the subject is an attribute defined in __init__()."""
        # An instance variable defined in __init__().
        if self.get_attribute_comment(parent, self.objpath[-1]):  # type: ignore[attr-defined]
            return True
        if self.is_runtime_instance_attribute_not_commented(parent):
            return True
        return False

    def is_runtime_instance_attribute_not_commented(self, parent: Any) -> bool:
        """Check the subject is an attribute defined in __init__() without comment."""
        for cls in inspect.getmro(parent):
            try:
                module = safe_getattr(cls, '__module__')
                qualname = safe_getattr(cls, '__qualname__')

                analyzer = ModuleAnalyzer.for_module(module)
                analyzer.analyze()
                if qualname and self.objpath:
                    key = '.'.join([qualname, self.objpath[-1]])
                    if key in analyzer.tagorder:
                        return True
            except (AttributeError, PycodeError):
                pass

        return False

    def import_object(self, raiseerror: bool = False) -> bool:
        """Check the existence of runtime instance attribute after failing to import the
        attribute."""
        try:
            return super().import_object(raiseerror=True)  # type: ignore[misc]
        except ImportError as exc:
            try:
                with mock(self.config.autodoc_mock_imports):
                    ret = import_object(self.modname, self.objpath[:-1], 'class',
                                        attrgetter=self.get_attr,  # type: ignore[attr-defined]
                                        warningiserror=self.config.autodoc_warningiserror)
                    parent = ret[3]
                    if self.is_runtime_instance_attribute(parent):
                        self.object = self.RUNTIME_INSTANCE_ATTRIBUTE
                        self.parent = parent
                        return True
            except ImportError:
                pass

            if raiseerror:
                raise
            logger.warning(exc.args[0], type='autodoc', subtype='import_object')
            self.env.note_reread()
            return False

    def should_suppress_value_header(self) -> bool:
        return (self.object is self.RUNTIME_INSTANCE_ATTRIBUTE or
                super().should_suppress_value_header())

    def get_doc(self) -> list[list[str]] | None:
        if (self.object is self.RUNTIME_INSTANCE_ATTRIBUTE and
                self.is_runtime_instance_attribute_not_commented(self.parent)):
            return None
        else:
            return super().get_doc()  # type: ignore[misc]


class UninitializedInstanceAttributeMixin(DataDocumenterMixinBase):
    """
    Mixin for AttributeDocumenter to provide the feature for supporting uninitialized
    instance attributes (PEP-526 styled, annotation only attributes).

    Example:

        class Foo:
            attr: int  #: This is a target of this mix-in.
    """

    def is_uninitialized_instance_attribute(self, parent: Any) -> bool:
        """Check the subject is an annotation only attribute."""
        annotations = get_type_hints(parent, None, self.config.autodoc_type_aliases)
        return self.objpath[-1] in annotations

    def import_object(self, raiseerror: bool = False) -> bool:
        """Check the exisitence of uninitialized instance attribute when failed to import
        the attribute."""
        try:
            return super().import_object(raiseerror=True)  # type: ignore[misc]
        except ImportError as exc:
            try:
                ret = import_object(self.modname, self.objpath[:-1], 'class',
                                    attrgetter=self.get_attr,  # type: ignore[attr-defined]
                                    warningiserror=self.config.autodoc_warningiserror)
                parent = ret[3]
                if self.is_uninitialized_instance_attribute(parent):
                    self.object = UNINITIALIZED_ATTR
                    self.parent = parent
                    return True
            except ImportError:
                pass

            if raiseerror:
                raise
            logger.warning(exc.args[0], type='autodoc', subtype='import_object')
            self.env.note_reread()
            return False

    def should_suppress_value_header(self) -> bool:
        return (self.object is UNINITIALIZED_ATTR or
                super().should_suppress_value_header())

    def get_doc(self) -> list[list[str]] | None:
        if self.object is UNINITIALIZED_ATTR:
            return None
        return super().get_doc()  # type: ignore[misc]


class AttributeDocumenter(GenericAliasMixin, SlotsMixin,  # type: ignore[misc]
                          RuntimeInstanceAttributeMixin,
                          UninitializedInstanceAttributeMixin, NonDataDescriptorMixin,
                          DocstringStripSignatureMixin, ClassLevelDocumenter):
    """
    Specialized Documenter subclass for attributes.
    """
    objtype = 'attribute'
    member_order = 60
    option_spec: OptionSpec = dict(ModuleLevelDocumenter.option_spec)
    option_spec["annotation"] = annotation_option
    option_spec["no-value"] = bool_option

    # must be higher than the MethodDocumenter, else it will recognize
    # some non-data descriptors as methods
    priority = 10

    @staticmethod
    def is_function_or_method(obj: Any) -> bool:
        return inspect.isfunction(obj) or inspect.isbuiltin(obj) or inspect.ismethod(obj)

    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any,
                            ) -> bool:
        if isinstance(parent, ModuleDocumenter):
            return False
        if inspect.isattributedescriptor(member):
            return True
        if not inspect.isroutine(member) and not isinstance(member, type):
            return True
        return False

    def document_members(self, all_members: bool = False) -> None:
        pass

    def update_annotations(self, parent: Any) -> None:
        """Update __annotations__ to support type_comment and so on."""
        try:
            annotations = dict(inspect.getannotations(parent))
            parent.__annotations__ = annotations

            for cls in inspect.getmro(parent):
                try:
                    module = safe_getattr(cls, '__module__')
                    qualname = safe_getattr(cls, '__qualname__')

                    analyzer = ModuleAnalyzer.for_module(module)
                    analyzer.analyze()
                    for (classname, attrname), annotation in analyzer.annotations.items():
                        if classname == qualname and attrname not in annotations:
                            annotations[attrname] = annotation
                except (AttributeError, PycodeError):
                    pass
        except (AttributeError, TypeError):
            # Failed to set __annotations__ (built-in, extensions, etc.)
            pass

    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror)
        if inspect.isenumattribute(self.object):
            self.object = self.object.value
        if self.parent:
            self.update_annotations(self.parent)

        return ret

    def get_real_modname(self) -> str:
        real_modname = self.get_attr(self.parent or self.object, '__module__', None)
        return real_modname or self.modname

    def should_suppress_value_header(self) -> bool:
        if super().should_suppress_value_header():
            return True
        else:
            doc = self.get_doc()
            if doc:
                docstring, metadata = separate_metadata('\n'.join(sum(doc, [])))
                if 'hide-value' in metadata:
                    return True

        return False

    def add_directive_header(self, sig: str) -> None:
        super().add_directive_header(sig)
        sourcename = self.get_sourcename()
        if self.options.annotation is SUPPRESS or self.should_suppress_directive_header():
            pass
        elif self.options.annotation:
            self.add_line('   :annotation: %s' % self.options.annotation, sourcename)
        else:
            if self.config.autodoc_typehints != 'none':
                # obtain type annotation for this attribute
                annotations = get_type_hints(self.parent, None,
                                             self.config.autodoc_type_aliases)
                if self.objpath[-1] in annotations:
                    if self.config.autodoc_typehints_format == "short":
                        objrepr = stringify_annotation(annotations.get(self.objpath[-1]),
                                                       "smart")
                    else:
                        objrepr = stringify_annotation(annotations.get(self.objpath[-1]),
                                                       "fully-qualified-except-typing")
                    self.add_line('   :type: ' + objrepr, sourcename)

            try:
                if (self.options.no_value or self.should_suppress_value_header() or
                        ismock(self.object)):
                    pass
                else:
                    objrepr = object_description(self.object)
                    self.add_line('   :value: ' + objrepr, sourcename)
            except ValueError:
                pass

    def get_attribute_comment(self, parent: Any, attrname: str) -> list[str] | None:
        for cls in inspect.getmro(parent):
            try:
                module = safe_getattr(cls, '__module__')
                qualname = safe_getattr(cls, '__qualname__')

                analyzer = ModuleAnalyzer.for_module(module)
                analyzer.analyze()
                if qualname and self.objpath:
                    key = (qualname, attrname)
                    if key in analyzer.attr_docs:
                        return list(analyzer.attr_docs[key])
            except (AttributeError, PycodeError):
                pass

        return None

    def get_doc(self) -> list[list[str]] | None:
        # Check the attribute has a docstring-comment
        comment = self.get_attribute_comment(self.parent, self.objpath[-1])
        if comment:
            return [comment]

        try:
            # Disable `autodoc_inherit_docstring` temporarily to avoid to obtain
            # a docstring from the value which descriptor returns unexpectedly.
            # ref: https://github.com/sphinx-doc/sphinx/issues/7805
            orig = self.config.autodoc_inherit_docstrings
            self.config.autodoc_inherit_docstrings = False  # type: ignore[attr-defined]
            return super().get_doc()
        finally:
            self.config.autodoc_inherit_docstrings = orig  # type: ignore[attr-defined]

    def add_content(self, more_content: StringList | None) -> None:
        # Disable analyzing attribute comment on Documenter.add_content() to control it on
        # AttributeDocumenter.add_content()
        self.analyzer = None

        if more_content is None:
            more_content = StringList()
        self.update_content(more_content)
        super().add_content(more_content)


class PropertyDocumenter(DocstringStripSignatureMixin,  # type: ignore[misc]
                         ClassLevelDocumenter):
    """
    Specialized Documenter subclass for properties.
    """
    objtype = 'property'
    member_order = 60

    # before AttributeDocumenter
    priority = AttributeDocumenter.priority + 1

    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool, parent: Any,
                            ) -> bool:
        if isinstance(parent, ClassDocumenter):
            if inspect.isproperty(member):
                return True
            else:
                __dict__ = safe_getattr(parent.object, '__dict__', {})
                obj = __dict__.get(membername)
                return isinstance(obj, classmethod) and inspect.isproperty(obj.__func__)
        else:
            return False

    def import_object(self, raiseerror: bool = False) -> bool:
        """Check the exisitence of uninitialized instance attribute when failed to import
        the attribute."""
        ret = super().import_object(raiseerror)
        if ret and not inspect.isproperty(self.object):
            __dict__ = safe_getattr(self.parent, '__dict__', {})
            obj = __dict__.get(self.objpath[-1])
            if isinstance(obj, classmethod) and inspect.isproperty(obj.__func__):
                self.object = obj.__func__
                self.isclassmethod = True
                return True
            else:
                return False

        self.isclassmethod = False
        return ret

    def format_args(self, **kwargs: Any) -> str:
        func = self._get_property_getter()
        if func is None:
            return ''

        # update the annotations of the property getter
        self.env.app.emit('autodoc-before-process-signature', func, False)
        # correctly format the arguments for a property
        return super().format_args(**kwargs)

    def document_members(self, all_members: bool = False) -> None:
        pass

    def get_real_modname(self) -> str:
        real_modname = self.get_attr(self.parent or self.object, '__module__', None)
        return real_modname or self.modname

    def add_directive_header(self, sig: str) -> None:
        super().add_directive_header(sig)
        sourcename = self.get_sourcename()
        if inspect.isabstractmethod(self.object):
            self.add_line('   :abstractmethod:', sourcename)
        if self.isclassmethod:
            self.add_line('   :classmethod:', sourcename)

        func = self._get_property_getter()
        if func is None or self.config.autodoc_typehints == 'none':
            return

        try:
            signature = inspect.signature(func,
                                          type_aliases=self.config.autodoc_type_aliases)
            if signature.return_annotation is not Parameter.empty:
                if self.config.autodoc_typehints_format == "short":
                    objrepr = stringify_annotation(signature.return_annotation, "smart")
                else:
                    objrepr = stringify_annotation(signature.return_annotation,
                                                   "fully-qualified-except-typing")
                self.add_line('   :type: ' + objrepr, sourcename)
        except TypeError as exc:
            logger.warning(__("Failed to get a function signature for %s: %s"),
                           self.fullname, exc)
            pass
        except ValueError:
            pass

    def _get_property_getter(self):
        if safe_getattr(self.object, 'fget', None):  # property
            return self.object.fget
        if safe_getattr(self.object, 'func', None):  # cached_property
            return self.object.func
        return None


def autodoc_attrgetter(app: Sphinx, obj: Any, name: str, *defargs: Any) -> Any:
    """Alternative getattr() for types"""
    for typ, func in app.registry.autodoc_attrgettrs.items():
        if isinstance(obj, typ):
            return func(obj, name, *defargs)

    return safe_getattr(obj, name, *defargs)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_autodocumenter(ModuleDocumenter)
    app.add_autodocumenter(ClassDocumenter)
    app.add_autodocumenter(ExceptionDocumenter)
    app.add_autodocumenter(DataDocumenter)
    app.add_autodocumenter(FunctionDocumenter)
    app.add_autodocumenter(DecoratorDocumenter)
    app.add_autodocumenter(MethodDocumenter)
    app.add_autodocumenter(AttributeDocumenter)
    app.add_autodocumenter(PropertyDocumenter)

    app.add_config_value('autoclass_content', 'class', True, ENUM('both', 'class', 'init'))
    app.add_config_value('autodoc_member_order', 'alphabetical', True,
                         ENUM('alphabetical', 'bysource', 'groupwise'))
    app.add_config_value('autodoc_class_signature', 'mixed', True, ENUM('mixed', 'separated'))
    app.add_config_value('autodoc_default_options', {}, True)
    app.add_config_value('autodoc_docstring_signature', True, True)
    app.add_config_value('autodoc_mock_imports', [], True)
    app.add_config_value('autodoc_typehints', "signature", True,
                         ENUM("signature", "description", "none", "both"))
    app.add_config_value('autodoc_typehints_description_target', 'all', True,
                         ENUM('all', 'documented', 'documented_params'))
    app.add_config_value('autodoc_type_aliases', {}, True)
    app.add_config_value('autodoc_typehints_format', "short", 'env',
                         ENUM("fully-qualified", "short"))
    app.add_config_value('autodoc_warningiserror', True, True)
    app.add_config_value('autodoc_inherit_docstrings', True, True)
    app.add_event('autodoc-before-process-signature')
    app.add_event('autodoc-process-docstring')
    app.add_event('autodoc-process-signature')
    app.add_event('autodoc-skip-member')
    app.add_event('autodoc-process-bases')

    app.setup_extension('sphinx.ext.autodoc.preserve_defaults')
    app.setup_extension('sphinx.ext.autodoc.type_comment')
    app.setup_extension('sphinx.ext.autodoc.typehints')

    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
