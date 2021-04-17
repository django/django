# -*- coding: utf-8 -*-
# Copyright (c) 2017 Ian Stapleton Cordasco
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module containing the logic for the URIBuilder object."""
from . import compat
from . import normalizers
from . import uri


class URIBuilder(object):
    """Object to aid in building up a URI Reference from parts.

    .. note::

        This object should be instantiated by the user, but it's recommended
        that it is not provided with arguments. Instead, use the available
        method to populate the fields.

    """

    def __init__(self, scheme=None, userinfo=None, host=None, port=None,
                 path=None, query=None, fragment=None):
        """Initialize our URI builder.

        :param str scheme:
            (optional)
        :param str userinfo:
            (optional)
        :param str host:
            (optional)
        :param int port:
            (optional)
        :param str path:
            (optional)
        :param str query:
            (optional)
        :param str fragment:
            (optional)
        """
        self.scheme = scheme
        self.userinfo = userinfo
        self.host = host
        self.port = port
        self.path = path
        self.query = query
        self.fragment = fragment

    def __repr__(self):
        """Provide a convenient view of our builder object."""
        formatstr = ('URIBuilder(scheme={b.scheme}, userinfo={b.userinfo}, '
                     'host={b.host}, port={b.port}, path={b.path}, '
                     'query={b.query}, fragment={b.fragment})')
        return formatstr.format(b=self)

    def add_scheme(self, scheme):
        """Add a scheme to our builder object.

        After normalizing, this will generate a new URIBuilder instance with
        the specified scheme and all other attributes the same.

        .. code-block:: python

            >>> URIBuilder().add_scheme('HTTPS')
            URIBuilder(scheme='https', userinfo=None, host=None, port=None,
                    path=None, query=None, fragment=None)

        """
        scheme = normalizers.normalize_scheme(scheme)
        return URIBuilder(
            scheme=scheme,
            userinfo=self.userinfo,
            host=self.host,
            port=self.port,
            path=self.path,
            query=self.query,
            fragment=self.fragment,
        )

    def add_credentials(self, username, password):
        """Add credentials as the userinfo portion of the URI.

        .. code-block:: python

            >>> URIBuilder().add_credentials('root', 's3crete')
            URIBuilder(scheme=None, userinfo='root:s3crete', host=None,
                    port=None, path=None, query=None, fragment=None)

            >>> URIBuilder().add_credentials('root', None)
            URIBuilder(scheme=None, userinfo='root', host=None,
                    port=None, path=None, query=None, fragment=None)
        """
        if username is None:
            raise ValueError('Username cannot be None')
        userinfo = normalizers.normalize_username(username)

        if password is not None:
            userinfo = '{}:{}'.format(
                userinfo,
                normalizers.normalize_password(password),
            )

        return URIBuilder(
            scheme=self.scheme,
            userinfo=userinfo,
            host=self.host,
            port=self.port,
            path=self.path,
            query=self.query,
            fragment=self.fragment,
        )

    def add_host(self, host):
        """Add hostname to the URI.

        .. code-block:: python

            >>> URIBuilder().add_host('google.com')
            URIBuilder(scheme=None, userinfo=None, host='google.com',
                    port=None, path=None, query=None, fragment=None)

        """
        return URIBuilder(
            scheme=self.scheme,
            userinfo=self.userinfo,
            host=normalizers.normalize_host(host),
            port=self.port,
            path=self.path,
            query=self.query,
            fragment=self.fragment,
        )

    def add_port(self, port):
        """Add port to the URI.

        .. code-block:: python

            >>> URIBuilder().add_port(80)
            URIBuilder(scheme=None, userinfo=None, host=None, port='80',
                    path=None, query=None, fragment=None)

            >>> URIBuilder().add_port(443)
            URIBuilder(scheme=None, userinfo=None, host=None, port='443',
                    path=None, query=None, fragment=None)

        """
        port_int = int(port)
        if port_int < 0:
            raise ValueError(
                'ports are not allowed to be negative. You provided {}'.format(
                    port_int,
                )
            )
        if port_int > 65535:
            raise ValueError(
                'ports are not allowed to be larger than 65535. '
                'You provided {}'.format(
                    port_int,
                )
            )

        return URIBuilder(
            scheme=self.scheme,
            userinfo=self.userinfo,
            host=self.host,
            port='{}'.format(port_int),
            path=self.path,
            query=self.query,
            fragment=self.fragment,
        )

    def add_path(self, path):
        """Add a path to the URI.

        .. code-block:: python

            >>> URIBuilder().add_path('sigmavirus24/rfc3985')
            URIBuilder(scheme=None, userinfo=None, host=None, port=None,
                    path='/sigmavirus24/rfc3986', query=None, fragment=None)

            >>> URIBuilder().add_path('/checkout.php')
            URIBuilder(scheme=None, userinfo=None, host=None, port=None,
                    path='/checkout.php', query=None, fragment=None)

        """
        if not path.startswith('/'):
            path = '/{}'.format(path)

        return URIBuilder(
            scheme=self.scheme,
            userinfo=self.userinfo,
            host=self.host,
            port=self.port,
            path=normalizers.normalize_path(path),
            query=self.query,
            fragment=self.fragment,
        )

    def add_query_from(self, query_items):
        """Generate and add a query a dictionary or list of tuples.

        .. code-block:: python

            >>> URIBuilder().add_query_from({'a': 'b c'})
            URIBuilder(scheme=None, userinfo=None, host=None, port=None,
                    path=None, query='a=b+c', fragment=None)

            >>> URIBuilder().add_query_from([('a', 'b c')])
            URIBuilder(scheme=None, userinfo=None, host=None, port=None,
                    path=None, query='a=b+c', fragment=None)

        """
        query = normalizers.normalize_query(compat.urlencode(query_items))

        return URIBuilder(
            scheme=self.scheme,
            userinfo=self.userinfo,
            host=self.host,
            port=self.port,
            path=self.path,
            query=query,
            fragment=self.fragment,
        )

    def add_query(self, query):
        """Add a pre-formated query string to the URI.

        .. code-block:: python

            >>> URIBuilder().add_query('a=b&c=d')
            URIBuilder(scheme=None, userinfo=None, host=None, port=None,
                    path=None, query='a=b&c=d', fragment=None)

        """
        return URIBuilder(
            scheme=self.scheme,
            userinfo=self.userinfo,
            host=self.host,
            port=self.port,
            path=self.path,
            query=normalizers.normalize_query(query),
            fragment=self.fragment,
        )

    def add_fragment(self, fragment):
        """Add a fragment to the URI.

        .. code-block:: python

            >>> URIBuilder().add_fragment('section-2.6.1')
            URIBuilder(scheme=None, userinfo=None, host=None, port=None,
                    path=None, query=None, fragment='section-2.6.1')

        """
        return URIBuilder(
            scheme=self.scheme,
            userinfo=self.userinfo,
            host=self.host,
            port=self.port,
            path=self.path,
            query=self.query,
            fragment=normalizers.normalize_fragment(fragment),
        )

    def finalize(self):
        """Create a URIReference from our builder.

        .. code-block:: python

            >>> URIBuilder().add_scheme('https').add_host('github.com'
            ...     ).add_path('sigmavirus24/rfc3986').finalize().unsplit()
            'https://github.com/sigmavirus24/rfc3986'

            >>> URIBuilder().add_scheme('https').add_host('github.com'
            ...     ).add_path('sigmavirus24/rfc3986').add_credentials(
            ...     'sigmavirus24', 'not-re@l').finalize().unsplit()
            'https://sigmavirus24:not-re%40l@github.com/sigmavirus24/rfc3986'

        """
        return uri.URIReference(
            self.scheme,
            normalizers.normalize_authority(
                (self.userinfo, self.host, self.port)
            ),
            self.path,
            self.query,
            self.fragment,
        )
