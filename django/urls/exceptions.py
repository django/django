from __future__ import unicode_literals

import itertools

from django.http import Http404

from .utils import describe_constraints


class Resolver404(Http404):
    """
    Raised when an url cannot be resolved to a view.
    """
    @property
    def path(self):
        if self.args:
            return self.args[0].get('path', '')
        return ''

    @property
    def tried(self):
        if self.args:
            return self.args[0].get('tried', [])
        return []

    @property
    def tried_patterns(self):
        patterns = []
        for resolvers in self.tried:
            pattern = describe_constraints(itertools.chain.from_iterable(r.constraints for r in resolvers))
            url_name = getattr(resolvers[-1], 'url_name', None)
            if url_name:
                pattern += ' [name=%s]' % url_name
            patterns.append(pattern)
        return patterns


class NoReverseMatch(Exception):
    """
    Raised when reverse() cannot reconstruct a valid url.
    """
    pass
