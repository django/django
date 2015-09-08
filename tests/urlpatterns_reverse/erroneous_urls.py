import warnings

from django.conf.urls import url
from django.utils.deprecation import RemovedInDjango110Warning

from . import views

# Test deprecated behavior of passing strings as view to url().
# Some of these can be removed in Django 1.10 as they aren't convertable to
# callables.
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=RemovedInDjango110Warning)
    urlpatterns = [
        # View has erroneous import
        url(r'erroneous_inner/$', views.erroneous_view),
        # Module has erroneous import
        url(r'erroneous_outer/$', 'urlpatterns_reverse.erroneous_views_module.erroneous_view'),
        # Module is an unqualified string
        url(r'erroneous_unqualified/$', 'unqualified_view'),
        # View does not exist
        url(r'missing_inner/$', 'urlpatterns_reverse.views.missing_view'),
        # View is not a callable (string import; arbitrary Python object)
        url(r'uncallable-dotted/$', 'urlpatterns_reverse.views.uncallable'),
        # View is not a callable (explicit import; arbitrary Python object)
        url(r'uncallable-object/$', views.uncallable),
        # Module does not exist
        url(r'missing_outer/$', 'urlpatterns_reverse.missing_module.missing_view'),
        # Regex contains an error (refs #6170)
        url(r'(regex_error/$', views.empty_view),
    ]
