from __future__ import unicode_literals

import re

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.regex_helper import normalize
from django.utils.translation import get_language

from .exceptions import NoReverseMatch, Resolver404


class Constraint(object):
    def describe(self):
        """
        Return a concise description to be used as an error message.
        """
        return ""

    def match(self, path, request=None):
        """
        If this constraint matches, return (new_path, args, kwargs).
        Otherwise, raise a Resolver404.
        """
        raise NotImplementedError("Constraint subclasses should implement match()")

    def construct(self, url_object, *args, **kwargs):
        """
        (Partially) reconstruct url_object based on args and kwargs.
        Return (url_object, leftover_args, leftover_kwargs).
        Raise NoReverseMatch if the url cannot be reconstructed with these
        arguments.
        """
        raise NotImplementedError("Constraint subclasses should implement construct()")


class RegexPattern(Constraint):
    def __init__(self, regex):
        self._regex = force_text(regex)

    def describe(self):
        pattern = self.regex.pattern
        return str(pattern[1:]) if pattern.startswith('^') else str(pattern)

    def __repr__(self):
        return '<RegexPattern regex=%r>' % self._regex

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

    def match(self, path, request=None):
        match = self.regex.search(path)
        if match:
            kwargs = match.groupdict()
            args = match.groups() if not kwargs else ()
            new_path = path[match.end():]
            return new_path, args, kwargs
        raise Resolver404()

    def construct(self, url_object, *args, **kwargs):
        for pattern, params in reversed(self.normalized_patterns):
            if kwargs:
                if any(param not in kwargs for param in params):
                    continue
                subs = kwargs
                new_args = ()
                new_kwargs = {k: v for (k, v) in kwargs.items() if k not in params}
            elif args:
                if len(params) > len(args):
                    continue
                subs = dict(zip(params, args))
                new_args = args[len(params):]
                new_kwargs = {}
            elif params:
                continue
            else:
                subs, new_args, new_kwargs = {}, (), {}
            path = pattern % subs
            if self.regex.search(path):
                url_object.path += path
                return url_object, new_args, new_kwargs
        raise NoReverseMatch()


class LocalizedRegexPattern(RegexPattern):
    def __init__(self, regex):
        self._regex = regex
        self._regex_dict = {}
        self._normalized_dict = {}

    @property
    def regex(self):
        language_code = get_language()
        if language_code not in self._regex_dict:
            if isinstance(self._regex, six.string_types):
                regex = self._regex
            else:
                regex = force_text(self._regex)
            try:
                compiled_regex = re.compile(regex, re.UNICODE)
            except re.error as e:
                raise ImproperlyConfigured(
                    '"%s" is not a valid regular expression: %s' %
                    (regex, six.text_type(e)))

            self._regex_dict[language_code] = compiled_regex
        return self._regex_dict[language_code]

    @property
    def normalized_patterns(self):
        language_code = get_language()
        if language_code not in self._normalized_dict:
            self._normalized_dict[language_code] = normalize(self.regex.pattern)
        return self._normalized_dict[language_code]


class LocalePrefix(LocalizedRegexPattern):
    def __init__(self):
        super(LocalePrefix, self).__init__('')

    @property
    def regex(self):
        language_code = get_language()
        if language_code not in self._regex_dict:
            regex_compiled = re.compile('^%s/' % language_code, re.UNICODE)
            self._regex_dict[language_code] = regex_compiled
        return self._regex_dict[language_code]


class ScriptPrefix(Constraint):
    def match(self, path, request=None):
        if not path.startswith('/'):
            raise Resolver404()
        return path[1:], (), {}

    def construct(self, url_object, *args, **kwargs):
        from django.urls import get_script_prefix

        url_object.path = get_script_prefix()
        return url_object, args, kwargs
