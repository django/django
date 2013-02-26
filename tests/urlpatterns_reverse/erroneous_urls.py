from django.conf.urls import patterns, url

urlpatterns = patterns('',
    # View has erroneous import
    url(r'erroneous_inner/$', 'regressiontests.urlpatterns_reverse.views.erroneous_view'),
    # Module has erroneous import
    url(r'erroneous_outer/$', 'regressiontests.urlpatterns_reverse.erroneous_views_module.erroneous_view'),
    # View does not exist
    url(r'missing_inner/$', 'regressiontests.urlpatterns_reverse.views.missing_view'),
    # View is not callable
    url(r'uncallable/$', 'regressiontests.urlpatterns_reverse.views.uncallable'),
    # Module does not exist
    url(r'missing_outer/$', 'regressiontests.urlpatterns_reverse.missing_module.missing_view'),
    # Regex contains an error (refs #6170)
    url(r'(regex_error/$', 'regressiontestes.urlpatterns_reverse.views.empty_view'),
)
