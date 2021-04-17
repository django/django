# -*- coding: utf-8 -*-
# Copyright (c) 2014 Rackspace
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

"""
An implementation of semantics and validations described in RFC 3986.

See http://rfc3986.readthedocs.io/ for detailed documentation.

:copyright: (c) 2014 Rackspace
:license: Apache v2.0, see LICENSE for details
"""

from .api import iri_reference
from .api import IRIReference
from .api import is_valid_uri
from .api import normalize_uri
from .api import uri_reference
from .api import URIReference
from .api import urlparse
from .parseresult import ParseResult

__title__ = 'rfc3986'
__author__ = 'Ian Stapleton Cordasco'
__author_email__ = 'graffatcolmingov@gmail.com'
__license__ = 'Apache v2.0'
__copyright__ = 'Copyright 2014 Rackspace'
__version__ = '1.3.2'

__all__ = (
    'ParseResult',
    'URIReference',
    'IRIReference',
    'is_valid_uri',
    'normalize_uri',
    'uri_reference',
    'iri_reference',
    'urlparse',
    '__title__',
    '__author__',
    '__author_email__',
    '__license__',
    '__copyright__',
    '__version__',
)
