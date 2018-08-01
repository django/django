"""
Wrapper class that takes a list of template loaders as an argument and attempts
to load templates from them in order, caching the result.
"""

import hashlib

from django.template import TemplateDoesNotExist
from django.template.backends.django import copy_exception

from .base import Loader as BaseLoader


class Loader(BaseLoader):

    def __init__(self, engine, loaders):
        self.template_cache = {}
        self.get_template_cache = {}
        self.loaders = engine.get_template_loaders(loaders)
        super().__init__(engine)

    def get_contents(self, origin):
        return origin.loader.get_contents(origin)

    def get_template(self, template_name, skip=None):
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
        key = self.cache_key(template_name, skip)
        cached = self.get_template_cache.get(key)
        if cached:
            if isinstance(cached, type) and issubclass(cached, TemplateDoesNotExist):
                raise cached(template_name)
            elif isinstance(cached, TemplateDoesNotExist):
                raise copy_exception(cached)
            return cached

        try:
            template = super().get_template(template_name, skip)
        except TemplateDoesNotExist as e:
            self.get_template_cache[key] = copy_exception(e) if self.engine.debug else TemplateDoesNotExist
            raise
        else:
            self.get_template_cache[key] = template

        return template

    def get_template_sources(self, template_name):
        for loader in self.loaders:
            yield from loader.get_template_sources(template_name)

    def cache_key(self, template_name, skip=None):
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

        return '-'.join(s for s in (str(template_name), skip_prefix, dirs_prefix) if s)

    def generate_hash(self, values):
        return hashlib.sha1('|'.join(values).encode()).hexdigest()

    def reset(self):
        "Empty the template cache."
        self.template_cache.clear()
        self.get_template_cache.clear()
