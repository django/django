"""
Wrapper class that takes a list of template loaders as an argument and attempts
to load templates from them in order, caching the result.
"""

import hashlib
import warnings

from django.template import Origin, Template, TemplateDoesNotExist
from django.template.backends.django import copy_exception
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_bytes, force_text
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

    def get_template(self, template_name, template_dirs=None, skip=None):
        """
        Perform the caching that gives this loader its name. Often many of the
        templates attempted will be missing, so memory use is of concern here.
        To keep it in check, caching behavior is a little complicated when a
        template is not found. See ticket #26306 for more details.

        With template debugging disabled, cache the TemplateDoesNotExist class
        for every missing template and raise a new instance of it after
        fetching it from the cache.

        With template debugging enabled, a unique TemplateDoesNotExist object
        is cached for each missing template to preserve debug data. When
        raising an exception, Python sets __traceback__, __context__, and
        __cause__ attributes on it. Those attributes can contain references to
        all sorts of objects up the call chain and caching them creates a
        memory leak. Thus, unraised copies of the exceptions are cached and
        copies of those copies are raised after they're fetched from the cache.
        """
        key = self.cache_key(template_name, template_dirs, skip)
        cached = self.get_template_cache.get(key)
        if cached:
            if isinstance(cached, type) and issubclass(cached, TemplateDoesNotExist):
                raise cached(template_name)
            elif isinstance(cached, TemplateDoesNotExist):
                raise copy_exception(cached)
            return cached

        try:
            template = super(Loader, self).get_template(
                template_name, template_dirs, skip,
            )
        except TemplateDoesNotExist as e:
            self.get_template_cache[key] = copy_exception(e) if self.engine.debug else TemplateDoesNotExist
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

        return '-'.join(filter(bool, [force_text(template_name), skip_prefix, dirs_prefix]))

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
