import warnings

from django.core.exceptions import ImproperlyConfigured
from django.utils import lru_cache, six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from .base import Context, Lexer, Parser, Template, TemplateDoesNotExist
from .context import _builtin_context_processors

_context_instance_undefined = object()
_dictionary_undefined = object()
_dirs_undefined = object()


class Engine(object):

    def __init__(self, dirs=None, app_dirs=False,
                 allowed_include_roots=None, context_processors=None,
                 debug=False, loaders=None, string_if_invalid='',
                 file_charset='utf-8'):
        if dirs is None:
            dirs = []
        if allowed_include_roots is None:
            allowed_include_roots = []
        if context_processors is None:
            context_processors = []
        if loaders is None:
            loaders = ['django.template.loaders.filesystem.Loader']
            if app_dirs:
                loaders += ['django.template.loaders.app_directories.Loader']
        else:
            if app_dirs:
                raise ImproperlyConfigured(
                    "app_dirs must not be set when loaders is defined.")

        if isinstance(allowed_include_roots, six.string_types):
            raise ImproperlyConfigured(
                "allowed_include_roots must be a tuple, not a string.")

        self.dirs = dirs
        self.app_dirs = app_dirs
        self.allowed_include_roots = allowed_include_roots
        self.context_processors = context_processors
        self.debug = debug
        self.loaders = loaders
        self.string_if_invalid = string_if_invalid
        self.file_charset = file_charset

    @staticmethod
    @lru_cache.lru_cache()
    def get_default():
        """
        When only one DjangoTemplates backend is configured, returns it.

        Raises ImproperlyConfigured otherwise.

        This is required for preserving historical APIs that rely on a
        globally available, implicitly configured engine such as:

        >>> from django.template import Context, Template
        >>> template = Template("Hello {{ name }}!")
        >>> context = Context({'name': "world"})
        >>> template.render(context)
        'Hello world!'
        """
        # Since Engine is imported in django.template and since
        # DjangoTemplates is a wrapper around this Engine class,
        # local imports are required to avoid import loops.
        from django.template import engines
        from django.template.backends.django import DjangoTemplates
        django_engines = [engine for engine in engines.all()
                          if isinstance(engine, DjangoTemplates)]
        if len(django_engines) == 1:
            # Unwrap the Engine instance inside DjangoTemplates
            return django_engines[0].engine
        elif len(django_engines) == 0:
            raise ImproperlyConfigured(
                "No DjangoTemplates backend is configured.")
        else:
            raise ImproperlyConfigured(
                "Several DjangoTemplates backends are configured. "
                "You must select one explicitly.")

    @cached_property
    def template_context_processors(self):
        context_processors = _builtin_context_processors
        context_processors += tuple(self.context_processors)
        return tuple(import_string(path) for path in context_processors)

    @cached_property
    def template_loaders(self):
        return self.get_template_loaders(self.loaders)

    def get_template_loaders(self, template_loaders):
        loaders = []
        for template_loader in template_loaders:
            loader = self.find_template_loader(template_loader)
            if loader is not None:
                loaders.append(loader)
        return loaders

    def find_template_loader(self, loader):
        if isinstance(loader, (tuple, list)):
            args = list(loader[1:])
            loader = loader[0]
        else:
            args = []

        if isinstance(loader, six.string_types):
            loader_class = import_string(loader)

            if getattr(loader_class, '_accepts_engine_in_init', False):
                args.insert(0, self)
            else:
                warnings.warn(
                    "%s inherits from django.template.loader.BaseLoader "
                    "instead of django.template.loaders.base.Loader. " %
                    loader, RemovedInDjango20Warning, stacklevel=2)

            loader_instance = loader_class(*args)

            if not loader_instance.is_usable:
                warnings.warn(
                    "Your template loaders configuration includes %r, but "
                    "your Python installation doesn't support that type of "
                    "template loading. Consider removing that line from "
                    "your settings." % loader)
                return None
            else:
                return loader_instance

        else:
            raise ImproperlyConfigured(
                "Invalid value in template loaders configuration: %r" % loader)

    def find_template(self, name, dirs=None):
        for loader in self.template_loaders:
            try:
                source, display_name = loader(name, dirs)
                origin = self.make_origin(display_name, loader, name, dirs)
                return source, origin
            except TemplateDoesNotExist:
                pass
        raise TemplateDoesNotExist(name)

    def from_string(self, template_code):
        """
        Returns a compiled Template object for the given template code,
        handling template inheritance recursively.
        """
        return Template(template_code, engine=self)

    def get_template(self, template_name, dirs=_dirs_undefined):
        """
        Returns a compiled Template object for the given template name,
        handling template inheritance recursively.
        """
        if dirs is _dirs_undefined:
            dirs = None
        else:
            warnings.warn(
                "The dirs argument of get_template is deprecated.",
                RemovedInDjango20Warning, stacklevel=2)

        template, origin = self.find_template(template_name, dirs)
        if not hasattr(template, 'render'):
            # template needs to be compiled
            template = Template(template, origin, template_name, engine=self)
        return template

    # This method was originally a function defined in django.template.loader.
    # It was moved here in Django 1.8 when encapsulating the Django template
    # engine in this Engine class. It's still called by deprecated code but it
    # will be removed in Django 2.0. It's superseded by a new render_to_string
    # function in django.template.loader.

    def render_to_string(self, template_name, context=None,
                         context_instance=_context_instance_undefined,
                         dirs=_dirs_undefined,
                         dictionary=_dictionary_undefined):
        if context_instance is _context_instance_undefined:
            context_instance = None
        else:
            warnings.warn(
                "The context_instance argument of render_to_string is "
                "deprecated.", RemovedInDjango20Warning, stacklevel=2)
        if dirs is _dirs_undefined:
            # Do not set dirs to None here to avoid triggering the deprecation
            # warning in select_template or get_template.
            pass
        else:
            warnings.warn(
                "The dirs argument of render_to_string is deprecated.",
                RemovedInDjango20Warning, stacklevel=2)
        if dictionary is _dictionary_undefined:
            dictionary = None
        else:
            warnings.warn(
                "The dictionary argument of render_to_string was renamed to "
                "context.", RemovedInDjango20Warning, stacklevel=2)
            context = dictionary

        if isinstance(template_name, (list, tuple)):
            t = self.select_template(template_name, dirs)
        else:
            t = self.get_template(template_name, dirs)
        if not context_instance:
            # Django < 1.8 accepted a Context in `context` even though that's
            # unintended. Preserve this ability but don't rewrap `context`.
            if isinstance(context, Context):
                return t.render(context)
            else:
                return t.render(Context(context))
        if not context:
            return t.render(context_instance)
        # Add the context to the context stack, ensuring it gets removed again
        # to keep the context_instance in the same state it started in.
        with context_instance.push(context):
            return t.render(context_instance)

    def select_template(self, template_name_list, dirs=_dirs_undefined):
        """
        Given a list of template names, returns the first that can be loaded.
        """
        if dirs is _dirs_undefined:
            # Do not set dirs to None here to avoid triggering the deprecation
            # warning in get_template.
            pass
        else:
            warnings.warn(
                "The dirs argument of select_template is deprecated.",
                RemovedInDjango20Warning, stacklevel=2)

        if not template_name_list:
            raise TemplateDoesNotExist("No template names provided")
        not_found = []
        for template_name in template_name_list:
            try:
                return self.get_template(template_name, dirs)
            except TemplateDoesNotExist as exc:
                if exc.args[0] not in not_found:
                    not_found.append(exc.args[0])
                continue
        # If we get here, none of the templates could be loaded
        raise TemplateDoesNotExist(', '.join(not_found))

    def compile_string(self, template_string, origin):
        """
        Compiles template_string into a NodeList ready for rendering.
        """
        if self.debug:
            from .debug import DebugLexer, DebugParser
            lexer_class, parser_class = DebugLexer, DebugParser
        else:
            lexer_class, parser_class = Lexer, Parser
        lexer = lexer_class(template_string, origin)
        tokens = lexer.tokenize()
        parser = parser_class(tokens)
        return parser.parse()

    def make_origin(self, display_name, loader, name, dirs):
        if self.debug and display_name:
            # Inner import to avoid circular dependency
            from .loader import LoaderOrigin
            return LoaderOrigin(display_name, loader, name, dirs)
        else:
            return None
