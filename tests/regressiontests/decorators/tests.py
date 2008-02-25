from unittest import TestCase
from sys import version_info

from django.http import HttpResponse
from django.utils.functional import allow_lazy, lazy, memoize
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.views.decorators.vary import vary_on_headers, vary_on_cookie
from django.views.decorators.cache import cache_page, never_cache, cache_control
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required

def fully_decorated(request):
    """Expected __doc__"""
    return HttpResponse('<html><body>dummy</body></html>')
fully_decorated.anything = "Expected __dict__"

# django.views.decorators.http
fully_decorated = require_http_methods(["GET"])(fully_decorated)
fully_decorated = require_GET(fully_decorated)
fully_decorated = require_POST(fully_decorated)

# django.views.decorators.vary
fully_decorated = vary_on_headers('Accept-language')(fully_decorated)
fully_decorated = vary_on_cookie(fully_decorated)

# django.views.decorators.cache
fully_decorated = cache_page(60*15)(fully_decorated)
fully_decorated = cache_control(private=True)(fully_decorated)
fully_decorated = never_cache(fully_decorated)

# django.contrib.auth.decorators
fully_decorated = user_passes_test(lambda u:True)(fully_decorated)
fully_decorated = login_required(fully_decorated)
fully_decorated = permission_required('change_world')(fully_decorated)

# django.contrib.admin.views.decorators
fully_decorated = staff_member_required(fully_decorated)

# django.utils.functional
fully_decorated = memoize(fully_decorated, {}, 1)
fully_decorated = allow_lazy(fully_decorated)
fully_decorated = lazy(fully_decorated)

class DecoratorsTest(TestCase):

    def test_attributes(self):
        """
        Tests that django decorators set certain attributes of the wrapped
        function.
        """
        # Only check __name__ on Python 2.4 or later since __name__ can't be
        # assigned to in earlier Python versions.
        if version_info[0] >= 2 and version_info[1] >= 4:
            self.assertEquals(fully_decorated.__name__, 'fully_decorated')
        self.assertEquals(fully_decorated.__doc__, 'Expected __doc__')
        self.assertEquals(fully_decorated.__dict__['anything'], 'Expected __dict__')
