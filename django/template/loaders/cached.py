"""
Wrapper class that takes a list of template loaders as an argument and attempts
to load templates from them in order, caching the result.
"""

import hashlib
from django.template.base import TemplateDoesNotExist
from django.template.loader import BaseLoader, get_template_from_string, find_template_loader, make_origin
from django.utils.encoding import force_bytes


class Loader(BaseLoader):
    is_usable = True

    def __init__(self, loaders):
        self.template_cache = {}
        self.find_template_cache = {}
        self._loaders = loaders
        self._cached_loaders = []

    @property
    def loaders(self):
        # Resolve loaders on demand to avoid circular imports
        if not self._cached_loaders:
            # Set self._cached_loaders atomically. Otherwise, another thread
            # could see an incomplete list. See #17303.
            cached_loaders = []
            for loader in self._loaders:
                cached_loaders.append(find_template_loader(loader))
            self._cached_loaders = cached_loaders
        return self._cached_loaders

    def cache_key(self, template_name, template_dirs):
        if template_dirs:
            # If template directories were specified, use a hash to differentiate
            return '-'.join([template_name, hashlib.sha1(force_bytes('|'.join(template_dirs))).hexdigest()])
        else:
            return template_name

    def find_template(self, name, dirs=None):
        """
        Helper method. Lookup the template :param name: in all the configured loaders
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
                    result = (template, make_origin(display_name, loader, name, dirs))
                    break
        self.find_template_cache[key] = result
        if result:
            return result
        else:
            self.template_cache[key] = TemplateDoesNotExist
            raise TemplateDoesNotExist(name)

    def load_template(self, template_name, template_dirs=None):
        key = self.cache_key(template_name, template_dirs)
        template_tuple = self.template_cache.get(key)
        # A cached previous failure:
        if template_tuple is TemplateDoesNotExist:
            raise TemplateDoesNotExist
        elif template_tuple is None:
            template, origin = self.find_template(template_name, template_dirs)
            if not hasattr(template, 'render'):
                try:
                    template = get_template_from_string(template, origin, template_name)
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
        self.find_template_cache.clear()
