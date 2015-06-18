from __future__ import unicode_literals

import re

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.functional import cached_property
from django.utils.regex_helper import normalize

from .exceptions import NoReverseMatch, Resolver404


class Constraint(object):
    def describe(self):
        """
        Return a concise description to be used as an error message.
        """
        return ""

    def match(self, url, request):
        """
        If this constraint matches, return (new_url, args, kwargs).
        Otherwise, raise a Resolver404.
        """
        raise NotImplementedError("Constraint subclasses should implement match()")

    def construct(self, url_object, args, kwargs):
        """
        (Partially) reconstruct url_object based on args and kwargs.
        Return (url_object, leftover_args, leftover_kwargs).
        Raise NoReverseMatch if the url cannot be reconstructed with these
        arguments.
        """
        raise NotImplementedError("Constraint subclasses should implement construct()")


class RegexPattern(Constraint):
    def __init__(self, regex):
        self._regex = regex

    def describe(self):
        return self.regex.pattern

    def __repr__(self):
        return '<RegexPattern %r>' % self._regex

    @cached_property
    def regex(self):
        try:
            compiled_regex = re.compile(self._regex, re.UNICODE)
        except re.error as e:
            raise ImproperlyConfigured(
                '"%s" is not a valid regular expression: %s' %
                (self._regex, six.text_type(e)))
        return compiled_regex

    @cached_property
    def normalized_patterns(self):
        return normalize(self.regex.pattern)

    def match(self, url, request):
        match = self.regex.search(url)
        if match:
            kwargs = match.groupdict()
            args = match.groups() if not kwargs else ()
            new_url = url[match.end():]
            return new_url, args, kwargs
        raise Resolver404()

    def construct(self, url_object, args, kwargs):
        for pattern, params in reversed(self.normalized_patterns):
            if kwargs:
                if any(param not in kwargs for param in params):
                    continue
                subs = kwargs
                new_args = ()
                new_kwargs = {k: v for (k, v) in kwargs.items() if k not in params}
            else:
                if len(params) > len(args):
                    continue
                subs = dict(zip(params, args))
                new_args = args[len(params):]
                new_kwargs = {}
            path = pattern % subs
            if self.regex.search(path):
                url_object.path += path
                return url_object, new_args, new_kwargs
        raise NoReverseMatch()