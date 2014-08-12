import warnings

from django.conf.urls import url

from . import views

# Test deprecated behavior of passing strings as view to url().
# Some of these can be removed in Django 2.0 as they aren't convertable to
# callabls.
with warnings.catch_warnings(record=True):
    warnings.filterwarnings('ignore', module='django.conf.urls')
    urlpatterns = [
        # View has erroneous import
        url(r'erroneous_inner/$', views.erroneous_view),
        # Module has erroneous import
        url(r'erroneous_outer/$', 'urlpatterns_reverse.erroneous_views_module.erroneous_view'),
        # Module is an unqualified string
        url(r'erroneous_unqualified/$', 'unqualified_view'),
        # View does not exist
        url(r'missing_inner/$', 'urlpatterns_reverse.views.missing_view'),
        # View is not callable
        url(r'uncallable/$', 'urlpatterns_reverse.views.uncallable'),
        # Module does not exist
        url(r'missing_outer/$', 'urlpatterns_reverse.missing_module.missing_view'),
        # Regex contains an error (refs #6170)
        url(r'(regex_error/$', views.empty_view),
    ]
