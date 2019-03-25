# -*- coding: utf-8 -*-
"""
    sphinx.registry
    ~~~~~~~~~~~~~~~

    Sphinx component registry.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import print_function

import traceback
import warnings
from inspect import isclass
from types import MethodType

from docutils.parsers.rst import Directive
from pkg_resources import iter_entry_points
from six import iteritems, itervalues

from sphinx.deprecation import RemovedInSphinx30Warning
from sphinx.domains import ObjType
from sphinx.domains.std import GenericObject, Target
from sphinx.errors import ExtensionError, SphinxError, VersionRequirementError
from sphinx.extension import Extension
from sphinx.locale import __
from sphinx.parsers import Parser as SphinxParser
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.docutils import directive_helper

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Iterator, List, Tuple, Type, Union  # NOQA
    from docutils import nodes  # NOQA
    from docutils.io import Input  # NOQA
    from docutils.parsers import Parser  # NOQA
    from docutils.transforms import Transform  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.config import Config  # NOQA
    from sphinx.domains import Domain, Index  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA
    from sphinx.ext.autodoc import Documenter  # NOQA
    from sphinx.util.typing import RoleFunction, TitleGetter  # NOQA

logger = logging.getLogger(__name__)

# list of deprecated extensions. Keys are extension name.
# Values are Sphinx version that merge the extension.
EXTENSION_BLACKLIST = {
    "sphinxjp.themecore": "1.2"
}  # type: Dict[unicode, unicode]


class SphinxComponentRegistry(object):
    def __init__(self):
        # type: () -> None
        #: special attrgetter for autodoc; class object -> attrgetter
        self.autodoc_attrgettrs = {}    # type: Dict[Type, Callable[[Any, unicode, Any], Any]]

        #: builders; a dict of builder name -> bulider class
        self.builders = {}              # type: Dict[unicode, Type[Builder]]

        #: autodoc documenters; a dict of documenter name -> documenter class
        self.documenters = {}           # type: Dict[unicode, Type[Documenter]]

        #: css_files; a list of tuple of filename and attributes
        self.css_files = []             # type: List[Tuple[unicode, Dict[unicode, unicode]]]

        #: domains; a dict of domain name -> domain class
        self.domains = {}               # type: Dict[unicode, Type[Domain]]

        #: additional directives for domains
        #: a dict of domain name -> dict of directive name -> directive
        self.domain_directives = {}     # type: Dict[unicode, Dict[unicode, Any]]

        #: additional indices for domains
        #: a dict of domain name -> list of index class
        self.domain_indices = {}        # type: Dict[unicode, List[Type[Index]]]

        #: additional object types for domains
        #: a dict of domain name -> dict of objtype name -> objtype
        self.domain_object_types = {}   # type: Dict[unicode, Dict[unicode, ObjType]]

        #: additional roles for domains
        #: a dict of domain name -> dict of role name -> role impl.
        self.domain_roles = {}          # type: Dict[unicode, Dict[unicode, Union[RoleFunction, XRefRole]]]  # NOQA

        #: additional enumerable nodes
        #: a dict of node class -> tuple of figtype and title_getter function
        self.enumerable_nodes = {}      # type: Dict[nodes.Node, Tuple[unicode, TitleGetter]]

        #: HTML inline and block math renderers
        #: a dict of name -> tuple of visit function and depart function
        self.html_inline_math_renderers = {}    # type: Dict[unicode, Tuple[Callable, Callable]]  # NOQA
        self.html_block_math_renderers = {}     # type: Dict[unicode, Tuple[Callable, Callable]]  # NOQA

        #: js_files; list of JS paths or URLs
        self.js_files = []              # type: List[Tuple[unicode, Dict[unicode, unicode]]]

        #: LaTeX packages; list of package names and its options
        self.latex_packages = []        # type: List[Tuple[unicode, unicode]]

        #: post transforms; list of transforms
        self.post_transforms = []       # type: List[Type[Transform]]

        #: source paresrs; file type -> parser class
        self.source_parsers = {}        # type: Dict[unicode, Type[Parser]]

        #: source inputs; file type -> input class
        self.source_inputs = {}         # type: Dict[unicode, Input]

        #: source suffix: suffix -> file type
        self.source_suffix = {}         # type: Dict[unicode, unicode]

        #: custom translators; builder name -> translator class
        self.translators = {}           # type: Dict[unicode, nodes.NodeVisitor]

        #: custom handlers for translators
        #: a dict of builder name -> dict of node name -> visitor and departure functions
        self.translation_handlers = {}  # type: Dict[unicode, Dict[unicode, Tuple[Callable, Callable]]]  # NOQA

        #: additional transforms; list of transforms
        self.transforms = []            # type: List[Type[Transform]]

    def add_builder(self, builder, override=False):
        # type: (Type[Builder], bool) -> None
        logger.debug('[app] adding builder: %r', builder)
        if not hasattr(builder, 'name'):
            raise ExtensionError(__('Builder class %s has no "name" attribute') % builder)
        if builder.name in self.builders and not override:
            raise ExtensionError(__('Builder %r already exists (in module %s)') %
                                 (builder.name, self.builders[builder.name].__module__))
        self.builders[builder.name] = builder

    def preload_builder(self, app, name):
        # type: (Sphinx, unicode) -> None
        if name is None:
            return

        if name not in self.builders:
            entry_points = iter_entry_points('sphinx.builders', name)
            try:
                entry_point = next(entry_points)
            except StopIteration:
                raise SphinxError(__('Builder name %s not registered or available'
                                     ' through entry point') % name)

            self.load_extension(app, entry_point.module_name)

    def create_builder(self, app, name):
        # type: (Sphinx, unicode) -> Builder
        if name not in self.builders:
            raise SphinxError(__('Builder name %s not registered') % name)

        return self.builders[name](app)

    def add_domain(self, domain, override=False):
        # type: (Type[Domain], bool) -> None
        logger.debug('[app] adding domain: %r', domain)
        if domain.name in self.domains and not override:
            raise ExtensionError(__('domain %s already registered') % domain.name)
        self.domains[domain.name] = domain

    def has_domain(self, domain):
        # type: (unicode) -> bool
        return domain in self.domains

    def create_domains(self, env):
        # type: (BuildEnvironment) -> Iterator[Domain]
        for DomainClass in itervalues(self.domains):
            domain = DomainClass(env)

            # transplant components added by extensions
            domain.directives.update(self.domain_directives.get(domain.name, {}))
            domain.roles.update(self.domain_roles.get(domain.name, {}))
            domain.indices.extend(self.domain_indices.get(domain.name, []))
            for name, objtype in iteritems(self.domain_object_types.get(domain.name, {})):
                domain.add_object_type(name, objtype)

            yield domain

    def override_domain(self, domain):
        # type: (Type[Domain]) -> None
        warnings.warn('registry.override_domain() is deprecated. '
                      'Use app.add_domain(domain, override=True) instead.',
                      RemovedInSphinx30Warning, stacklevel=2)
        self.add_domain(domain, override=True)

    def add_directive_to_domain(self, domain, name, obj, has_content=None, argument_spec=None,
                                override=False, **option_spec):
        # type: (unicode, unicode, Any, bool, Any, bool, Any) -> None
        logger.debug('[app] adding directive to domain: %r',
                     (domain, name, obj, has_content, argument_spec, option_spec))
        if domain not in self.domains:
            raise ExtensionError(__('domain %s not yet registered') % domain)

        directives = self.domain_directives.setdefault(domain, {})
        if name in directives and not override:
            raise ExtensionError(__('The %r directive is already registered to domain %s') %
                                 (name, domain))
        if not isclass(obj) or not issubclass(obj, Directive):
            directives[name] = directive_helper(obj, has_content, argument_spec, **option_spec)
        else:
            directives[name] = obj

    def add_role_to_domain(self, domain, name, role, override=False):
        # type: (unicode, unicode, Union[RoleFunction, XRefRole], bool) -> None
        logger.debug('[app] adding role to domain: %r', (domain, name, role))
        if domain not in self.domains:
            raise ExtensionError(__('domain %s not yet registered') % domain)
        roles = self.domain_roles.setdefault(domain, {})
        if name in roles and not override:
            raise ExtensionError(__('The %r role is already registered to domain %s') %
                                 (name, domain))
        roles[name] = role

    def add_index_to_domain(self, domain, index, override=False):
        # type: (unicode, Type[Index], bool) -> None
        logger.debug('[app] adding index to domain: %r', (domain, index))
        if domain not in self.domains:
            raise ExtensionError(__('domain %s not yet registered') % domain)
        indices = self.domain_indices.setdefault(domain, [])
        if index in indices and not override:
            raise ExtensionError(__('The %r index is already registered to domain %s') %
                                 (index.name, domain))
        indices.append(index)

    def add_object_type(self, directivename, rolename, indextemplate='',
                        parse_node=None, ref_nodeclass=None, objname='',
                        doc_field_types=[], override=False):
        # type: (unicode, unicode, unicode, Callable, nodes.Node, unicode, List, bool) -> None
        logger.debug('[app] adding object type: %r',
                     (directivename, rolename, indextemplate, parse_node,
                      ref_nodeclass, objname, doc_field_types))

        # create a subclass of GenericObject as the new directive
        directive = type(directivename,  # type: ignore
                         (GenericObject, object),
                         {'indextemplate': indextemplate,
                          'parse_node': staticmethod(parse_node),
                          'doc_field_types': doc_field_types})

        self.add_directive_to_domain('std', directivename, directive)
        self.add_role_to_domain('std', rolename, XRefRole(innernodeclass=ref_nodeclass))

        object_types = self.domain_object_types.setdefault('std', {})
        if directivename in object_types and not override:
            raise ExtensionError(__('The %r object_type is already registered') %
                                 directivename)
        object_types[directivename] = ObjType(objname or directivename, rolename)

    def add_crossref_type(self, directivename, rolename, indextemplate='',
                          ref_nodeclass=None, objname='', override=False):
        # type: (unicode, unicode, unicode, nodes.Node, unicode, bool) -> None
        logger.debug('[app] adding crossref type: %r',
                     (directivename, rolename, indextemplate, ref_nodeclass, objname))

        # create a subclass of Target as the new directive
        directive = type(directivename,  # type: ignore
                         (Target, object),
                         {'indextemplate': indextemplate})

        self.add_directive_to_domain('std', directivename, directive)
        self.add_role_to_domain('std', rolename, XRefRole(innernodeclass=ref_nodeclass))

        object_types = self.domain_object_types.setdefault('std', {})
        if directivename in object_types and not override:
            raise ExtensionError(__('The %r crossref_type is already registered') %
                                 directivename)
        object_types[directivename] = ObjType(objname or directivename, rolename)

    def add_source_suffix(self, suffix, filetype, override=False):
        # type: (unicode, unicode, bool) -> None
        logger.debug('[app] adding source_suffix: %r, %r', suffix, filetype)
        if suffix in self.source_suffix and not override:
            raise ExtensionError(__('source_suffix %r is already registered') % suffix)
        else:
            self.source_suffix[suffix] = filetype

    def add_source_parser(self, *args, **kwargs):
        # type: (Any, bool) -> None
        logger.debug('[app] adding search source_parser: %r', args)
        if len(args) == 1:
            # new sytle arguments: (source_parser)
            suffix = None       # type: unicode
            parser = args[0]    # type: Type[Parser]
        else:
            # old style arguments: (suffix, source_parser)
            warnings.warn('app.add_source_parser() does not support suffix argument. '
                          'Use app.add_source_suffix() instead.',
                          RemovedInSphinx30Warning, stacklevel=3)
            suffix = args[0]
            parser = args[1]

        if suffix:
            self.add_source_suffix(suffix, suffix, override=True)

        if len(parser.supported) == 0:
            warnings.warn('Old source_parser has been detected. Please fill Parser.supported '
                          'attribute: %s' % parser.__name__,
                          RemovedInSphinx30Warning, stacklevel=3)

        # create a map from filetype to parser
        for filetype in parser.supported:
            if filetype in self.source_parsers and not kwargs.get('override'):
                raise ExtensionError(__('source_parser for %r is already registered') %
                                     filetype)
            else:
                self.source_parsers[filetype] = parser

        # also maps suffix to parser
        #
        # This rescues old styled parsers which does not have ``supported`` filetypes.
        if suffix:
            self.source_parsers[suffix] = parser

    def get_source_parser(self, filetype):
        # type: (unicode) -> Type[Parser]
        try:
            return self.source_parsers[filetype]
        except KeyError:
            raise SphinxError(__('Source parser for %s not registered') % filetype)

    def get_source_parsers(self):
        # type: () -> Dict[unicode, Parser]
        return self.source_parsers

    def create_source_parser(self, app, filename):
        # type: (Sphinx, unicode) -> Parser
        parser_class = self.get_source_parser(filename)
        parser = parser_class()
        if isinstance(parser, SphinxParser):
            parser.set_application(app)
        return parser

    def add_source_input(self, input_class, override=False):
        # type: (Type[Input], bool) -> None
        for filetype in input_class.supported:
            if filetype in self.source_inputs and not override:
                raise ExtensionError(__('source_input for %r is already registered') %
                                     filetype)
            self.source_inputs[filetype] = input_class

    def get_source_input(self, filetype):
        # type: (unicode) -> Type[Input]
        try:
            return self.source_inputs[filetype]
        except KeyError:
            try:
                # use special source_input for unknown filetype
                return self.source_inputs['*']
            except KeyError:
                raise SphinxError(__('source_input for %s not registered') % filetype)

    def add_translator(self, name, translator, override=False):
        # type: (unicode, Type[nodes.NodeVisitor], bool) -> None
        logger.debug('[app] Change of translator for the %s builder.' % name)
        if name in self.translators and not override:
            raise ExtensionError(__('Translator for %r already exists') % name)
        self.translators[name] = translator

    def add_translation_handlers(self, node, **kwargs):
        # type: (nodes.Node, Any) -> None
        logger.debug('[app] adding translation_handlers: %r, %r', node, kwargs)
        for builder_name, handlers in iteritems(kwargs):
            translation_handlers = self.translation_handlers.setdefault(builder_name, {})
            try:
                visit, depart = handlers  # unpack once for assertion
                translation_handlers[node.__name__] = (visit, depart)
            except ValueError:
                raise ExtensionError(__('kwargs for add_node() must be a (visit, depart) '
                                        'function tuple: %r=%r') % builder_name, handlers)

    def get_translator_class(self, builder):
        # type: (Builder) -> Type[nodes.NodeVisitor]
        return self.translators.get(builder.name,
                                    builder.default_translator_class)

    def create_translator(self, builder, *args):
        # type: (Builder, Any) -> nodes.NodeVisitor
        translator_class = self.get_translator_class(builder)
        assert translator_class, "translator not found for %s" % builder.name
        translator = translator_class(*args)

        # transplant handlers for custom nodes to translator instance
        handlers = self.translation_handlers.get(builder.name, None)
        if handlers is None:
            # retry with builder.format
            handlers = self.translation_handlers.get(builder.format, {})

        for name, (visit, depart) in iteritems(handlers):
            setattr(translator, 'visit_' + name, MethodType(visit, translator))
            if depart:
                setattr(translator, 'depart_' + name, MethodType(depart, translator))

        return translator

    def add_transform(self, transform):
        # type: (Type[Transform]) -> None
        logger.debug('[app] adding transform: %r', transform)
        self.transforms.append(transform)

    def get_transforms(self):
        # type: () -> List[Type[Transform]]
        return self.transforms

    def add_post_transform(self, transform):
        # type: (Type[Transform]) -> None
        logger.debug('[app] adding post transform: %r', transform)
        self.post_transforms.append(transform)

    def get_post_transforms(self):
        # type: () -> List[Type[Transform]]
        return self.post_transforms

    def add_documenter(self, objtype, documenter):
        # type: (unicode, Type[Documenter]) -> None
        self.documenters[objtype] = documenter

    def add_autodoc_attrgetter(self, typ, attrgetter):
        # type: (Type, Callable[[Any, unicode, Any], Any]) -> None
        self.autodoc_attrgettrs[typ] = attrgetter

    def add_css_files(self, filename, **attributes):
        self.css_files.append((filename, attributes))

    def add_js_file(self, filename, **attributes):
        # type: (unicode, **unicode) -> None
        logger.debug('[app] adding js_file: %r, %r', filename, attributes)
        self.js_files.append((filename, attributes))  # type: ignore

    def add_latex_package(self, name, options):
        # type: (unicode, unicode) -> None
        logger.debug('[app] adding latex package: %r', name)
        self.latex_packages.append((name, options))

    def add_enumerable_node(self, node, figtype, title_getter=None, override=False):
        # type: (nodes.Node, unicode, TitleGetter, bool) -> None
        logger.debug('[app] adding enumerable node: (%r, %r, %r)', node, figtype, title_getter)
        if node in self.enumerable_nodes and not override:
            raise ExtensionError(__('enumerable_node %r already registered') % node)
        self.enumerable_nodes[node] = (figtype, title_getter)

    def add_html_math_renderer(self, name, inline_renderers, block_renderers):
        # type: (unicode, Tuple[Callable, Callable], Tuple[Callable, Callable]) -> None
        logger.debug('[app] adding html_math_renderer: %s, %r, %r',
                     name, inline_renderers, block_renderers)
        if name in self.html_inline_math_renderers:
            raise ExtensionError(__('math renderer %s is already registred') % name)

        self.html_inline_math_renderers[name] = inline_renderers
        self.html_block_math_renderers[name] = block_renderers

    def load_extension(self, app, extname):
        # type: (Sphinx, unicode) -> None
        """Load a Sphinx extension."""
        if extname in app.extensions:  # alread loaded
            return
        if extname in EXTENSION_BLACKLIST:
            logger.warning(__('the extension %r was already merged with Sphinx since '
                              'version %s; this extension is ignored.'),
                           extname, EXTENSION_BLACKLIST[extname])
            return

        # update loading context
        app._setting_up_extension.append(extname)

        try:
            mod = __import__(extname, None, None, ['setup'])
        except ImportError as err:
            logger.verbose(__('Original exception:\n') + traceback.format_exc())
            raise ExtensionError(__('Could not import extension %s') % extname, err)

        if not hasattr(mod, 'setup'):
            logger.warning(__('extension %r has no setup() function; is it really '
                              'a Sphinx extension module?'), extname)
            metadata = {}  # type: Dict[unicode, Any]
        else:
            try:
                metadata = mod.setup(app)
            except VersionRequirementError as err:
                # add the extension name to the version required
                raise VersionRequirementError(
                    __('The %s extension used by this project needs at least '
                       'Sphinx v%s; it therefore cannot be built with this '
                       'version.') % (extname, err)
                )

        if metadata is None:
            metadata = {}
        elif not isinstance(metadata, dict):
            logger.warning(__('extension %r returned an unsupported object from '
                              'its setup() function; it should return None or a '
                              'metadata dictionary'), extname)
            metadata = {}

        app.extensions[extname] = Extension(extname, mod, **metadata)
        app._setting_up_extension.pop()

    def get_envversion(self, app):
        # type: (Sphinx) -> Dict[unicode, unicode]
        from sphinx.environment import ENV_VERSION
        envversion = {ext.name: ext.metadata['env_version'] for ext in app.extensions.values()
                      if ext.metadata.get('env_version')}
        envversion['sphinx'] = ENV_VERSION
        return envversion


def merge_source_suffix(app, config):
    # type: (Sphinx, Config) -> None
    """Merge source_suffix which specified by user and added by extensions."""
    for suffix, filetype in iteritems(app.registry.source_suffix):
        if suffix not in app.config.source_suffix:
            app.config.source_suffix[suffix] = filetype
        elif app.config.source_suffix[suffix] is None:
            # filetype is not specified (default filetype).
            # So it overrides default filetype by extensions setting.
            app.config.source_suffix[suffix] = filetype

    # copy config.source_suffix to registry
    app.registry.source_suffix = app.config.source_suffix


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.connect('config-inited', merge_source_suffix)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
