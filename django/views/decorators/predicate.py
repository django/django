"""
Decorators for views based on HTTP headers.
"""

import logging
from functools import wraps

from django.utils.decorators import decorator_from_middleware, available_attrs
from django.utils.http import http_date
from django.middleware.http import ConditionalGetMiddleware

logger = logging.getLogger('django.request')


def url_predicates(predicates_list):
    """
    Decorators to make urls matchable if predicates return True
    Usage::

        url_pattern += url('/', my_view_GET)
        url_pattern += url('/', my_view_POST)

        ...

        predicate_GET = lambda request: request.method == 'GET'
        predicate_POST = lambda request: request.method == 'POST'

        @url_predicates([predicate_GET])
        def my_view_GET(request):
            # I can assume now that only GET requests get match to the url
            # associated to this view
            # ...

        @url_predicates([predicate_POST])
        def my_view_POST(request):
            # I can assume now that only POST requests get match to the url
            # associated to this view
            # ...
    """
    def decorator(func):
        @wraps(func, assigned=available_attrs(func))
        def inner(request, *args, **kwargs):
            return func(request, *args, **kwargs)
        inner.predicates = predicates_list
        return inner
    return decorator

