"""
Wrapper class that takes a list of template loaders as an argument and attempts
to load templates from them in order, caching the result.
"""

import hashlib
import warnings

from django.template import Origin, Template, TemplateDoesNotExist
from django.template.backends.django import copy_exception
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_bytes
from django.utils.inspect import func_supports_parameter

from .base import Loader as BaseLoader


class Loader(BaseLoader):

    def __init__(self, engine, loaders):
        self.template_cache = {}
        self.find_template_cache = {}  # RemovedInDjango20Warning
        self.get_template_cache = {}
        self.loaders = engine.get_template_loaders(loaders)
        super(Loader, self).__init__(engine)

    def get_contents(self, origin):
        return origin.loader.get_contents(origin)

    def _raise_from_cache(self, value, template_name):
        """
        Take a value pulled from the template cache and raise an exception if
        the value represents an error. If template debugging is off, the error
        value will be the raw TemplateDoesNotExist class, otherwise it will be
        an instance of TemplateDoesNotExist. In the latter case, we raise a
        new exception instead of raising the cached instance to prevent local
        state, including the traceback, from ending up in the template cache.
        """
        if isinstance(value, type) and issubclass(value, TemplateDoesNotExist):
            raise value(template_name)
        elif isinstance(value, TemplateDoesNotExist):
            raise copy_exception(value)

    def _exception_for_cache(self, exception):
        """
        Return an error value suitable for caching given a previously raised
        TemplateDoesNotExist exception. When template debugging is disabled,
        we just cache the TemplateDoesNotExist class to save memory. With
        template debugging enabled we want to keep the list of attempted
        template paths stored on the exception, but an exception that has been
        raised holds traceback and context data that we don't want to cache,
        so we instantiate a new, un-raised exception to put in the cache.
        """
        if self.engine.debug:
            return copy_exception(exception)
        else:
            return TemplateDoesNotExist

    def get_template(self, template_name, template_dirs=None, skip=None):
        key = self.cache_key(template_name, template_dirs, skip)
        cached = self.get_template_cache.get(key)
        if cached:
            self._raise_from_cache(cached, template_name)
            return cached

        try:
            template = super(Loader, self).get_template(
                template_name, template_dirs, skip,
            )
        except TemplateDoesNotExist as e:
            self.get_template_cache[key] = self._exception_for_cache(e)
            raise
        else:
            self.get_template_cache[key] = template

        return template

    def get_template_sources(self, template_name, template_dirs=None):
        for loader in self.loaders:
            args = [template_name]
            # RemovedInDjango20Warning: Add template_dirs for compatibility
            # with old loaders
            if func_supports_parameter(loader.get_template_sources, 'template_dirs'):
                args.append(template_dirs)
            for origin in loader.get_template_sources(*args):
                yield origin

    def cache_key(self, template_name, template_dirs, skip=None):
        """
        Generate a cache key for the template name, dirs, and skip.

        If skip is provided, only origins that match template_name are included
        in the cache key. This ensures each template is only parsed and cached
        once if contained in different extend chains like:

            x -> a -> a
            y -> a -> a
            z -> a -> a
        """
        dirs_prefix = ''
        skip_prefix = ''

        if skip:
            matching = [origin.name for origin in skip if origin.template_name == template_name]
            if matching:
                skip_prefix = self.generate_hash(matching)

        if template_dirs:
            dirs_prefix = self.generate_hash(template_dirs)

        return ("%s-%s-%s" % (template_name, skip_prefix, dirs_prefix)).strip('-')

    def generate_hash(self, values):
        return hashlib.sha1(force_bytes('|'.join(values))).hexdigest()

    @property
    def supports_recursion(self):
        """
        RemovedInDjango20Warning: This is an internal property used by the
        ExtendsNode during the deprecation of non-recursive loaders.
        """
        return all(hasattr(loader, 'get_contents') for loader in self.loaders)

    def find_template(self, name, dirs=None):
        """
        RemovedInDjango20Warning: An internal method to lookup the template
        name in all the configured loaders.
        """
        key = self.cache_key(name, dirs)
        try:
            result = self.find_template_cache[key]
        except KeyError:
            result = None
            for loader in self.loaders:
                try:
                    template, display_name = loader(name, dirs)
                except TemplateDoesNotExist:
                    pass
                else:
                    origin = Origin(
                        name=display_name,
                        template_name=name,
                        loader=loader,
                    )
                    result = template, origin
                    break
        self.find_template_cache[key] = result
        if result:
            return result
        else:
            self.template_cache[key] = TemplateDoesNotExist
            raise TemplateDoesNotExist(name)

    def load_template(self, template_name, template_dirs=None):
        warnings.warn(
            'The load_template() method is deprecated. Use get_template() '
            'instead.', RemovedInDjango20Warning,
        )
        key = self.cache_key(template_name, template_dirs)
        template_tuple = self.template_cache.get(key)
        # A cached previous failure:
        if template_tuple is TemplateDoesNotExist:
            raise TemplateDoesNotExist(template_name)
        elif template_tuple is None:
            template, origin = self.find_template(template_name, template_dirs)
            if not hasattr(template, 'render'):
                try:
                    template = Template(template, origin, template_name, self.engine)
                except TemplateDoesNotExist:
                    # If compiling the template we found raises TemplateDoesNotExist,
                    # back off to returning the source and display name for the template
                    # we were asked to load. This allows for correct identification (later)
                    # of the actual template that does not exist.
                    self.template_cache[key] = (template, origin)
            self.template_cache[key] = (template, None)
        return self.template_cache[key]

    def reset(self):
        "Empty the template cache."
        self.template_cache.clear()
        self.find_template_cache.clear()  # RemovedInDjango20Warning
        self.get_template_cache.clear()
