from __future__ import unicode_literals

from django.utils.functional import cached_property


class URL(object):
    def __init__(self, scheme='', host='', script_name='', path_info='', query_string='', fragment=''):
        self.scheme = scheme
        self.host = ''
        self.script_name = script_name
        self.path_info = path_info
        self.query_string = query_string
        self.fragment = fragment

    @cached_property
    def path(self):
        script_name = self.script_name
        # Be careful to only replace the first slash in the path because of
        # http://test/something and http://test//something being different.
        path_info = self.path_info.replace('/', '', 1) if self.path_info.startswith('/') else self.path_info
        return '%s/%s' % (script_name, path_info)

    def copy(self):
        return self.__class__(
            self.scheme, self.host, self.script_name,
            self.path_info, self.query_string, self.fragment
        )