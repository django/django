import warnings

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import lru_cache
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from .base import Context, Lexer, Parser, Template, TemplateDoesNotExist


_dirs_undefined = object()


class Engine(object):

    def __init__(self, dirs=None, app_dirs=False,
                 allowed_include_roots=None, context_processors=None,
                 loaders=None, string_if_invalid='',
                 file_charset=None):
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
                    "APP_DIRS must not be set when LOADERS is defined.")
        if file_charset is None:
            file_charset = 'utf-8'

        self.dirs = dirs
        self.app_dirs = app_dirs
        self.allowed_include_roots = allowed_include_roots
        self.context_processors = context_processors
        self.loaders = loaders
        self.string_if_invalid = string_if_invalid
        self.file_charset = file_charset

    @classmethod
    @lru_cache.lru_cache()
    def get_default(cls):
        """Transitional method for refactoring."""
        return cls(
            dirs=settings.TEMPLATE_DIRS,
            allowed_include_roots=settings.ALLOWED_INCLUDE_ROOTS,
            context_processors=settings.TEMPLATE_CONTEXT_PROCESSORS,
            loaders=settings.TEMPLATE_LOADERS,
            string_if_invalid=settings.TEMPLATE_STRING_IF_INVALID,
            file_charset=settings.FILE_CHARSET,
        )

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
            template = self.get_template_from_string(template, origin, template_name)
        return template

    def get_template_from_string(self, source, origin=None, name=None):
        """
        Returns a compiled Template object for the given template code,
        handling template inheritance recursively.
        """
        return Template(source, origin, name)

    def render_to_string(self, template_name, dictionary=None, context_instance=None,
                         dirs=_dirs_undefined):
        """
        Loads the given template_name and renders it with the given dictionary as
        context. The template_name may be a string to load a single template using
        get_template, or it may be a tuple to use select_template to find one of
        the templates in the list. Returns a string.
        """
        if dirs is _dirs_undefined:
            # Do not set dirs to None here to avoid triggering the deprecation
            # warning in select_template or get_template.
            pass
        else:
            warnings.warn(
                "The dirs argument of render_to_string is deprecated.",
                RemovedInDjango20Warning, stacklevel=2)

        if isinstance(template_name, (list, tuple)):
            t = self.select_template(template_name, dirs)
        else:
            t = self.get_template(template_name, dirs)
        if not context_instance:
            # Django < 1.8 accepted a Context in `dictionary` even though that's
            # unintended. Preserve this ability but don't rewrap `dictionary`.
            if isinstance(dictionary, Context):
                return t.render(dictionary)
            else:
                return t.render(Context(dictionary))
        if not dictionary:
            return t.render(context_instance)
        # Add the dictionary to the context stack, ensuring it gets removed again
        # to keep the context_instance in the same state it started in.
        with context_instance.push(dictionary):
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
        if settings.TEMPLATE_DEBUG:
            from .debug import DebugLexer, DebugParser
            lexer_class, parser_class = DebugLexer, DebugParser
        else:
            lexer_class, parser_class = Lexer, Parser
        lexer = lexer_class(template_string, origin)
        tokens = lexer.tokenize()
        parser = parser_class(tokens)
        return parser.parse()

    def make_origin(self, display_name, loader, name, dirs):
        if settings.TEMPLATE_DEBUG and display_name:
            # Inner import to avoid circular dependency
            from .loader import LoaderOrigin
            return LoaderOrigin(display_name, loader, name, dirs)
        else:
            return None
