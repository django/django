from django.conf.urls import url

from . import views

urlpatterns = [
    # View has erroneous import
    url(r'erroneous_inner/$', views.erroneous_view),
    # Module has erroneous import
    # Remove in Django 2.0 along with erroneous_views_module as this is only
    # an issue with string in urlpatterns
    url(r'erroneous_outer/$', 'urlpatterns_reverse.erroneous_views_module.erroneous_view'),
    # Module is an unqualified string
    url(r'erroneous_unqualified/$', 'unqualified_view'),
    # View does not exist
    # Remove in Django 2.0 along with erroneous_views_module as this is only
    # an issue with string in urlpatterns
    url(r'missing_inner/$', 'urlpatterns_reverse.views.missing_view'),
    # View is not callable
    # Remove in Django 2.0 along with erroneous_views_module as this is only
    # an issue with string in urlpatterns
    url(r'uncallable/$', 'urlpatterns_reverse.views.uncallable'),
    # Module does not exist
    url(r'missing_outer/$', 'urlpatterns_reverse.missing_module.missing_view'),
    # Regex contains an error (refs #6170)
    url(r'(regex_error/$', views.empty_view),
]
