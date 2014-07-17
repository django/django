from __future__ import absolute_import

from django.conf.urls import patterns, url, include

from .views import empty_view, empty_view_partial, empty_view_wrapped, absolute_kwargs_view


other_patterns = patterns('',
    url(r'non_path_include/$', empty_view, name='non_path_include'),
    url(r'nested_path/$', 'regressiontests.urlpatterns_reverse.views.nested_view'),
)

urlpatterns = patterns('',
    url(r'^places/(\d+)/$', empty_view, name='places'),
    url(r'^places?/$', empty_view, name="places?"),
    url(r'^places+/$', empty_view, name="places+"),
    url(r'^places*/$', empty_view, name="places*"),
    url(r'^(?:places/)?$', empty_view, name="places2?"),
    url(r'^(?:places/)+$', empty_view, name="places2+"),
    url(r'^(?:places/)*$', empty_view, name="places2*"),
    url(r'^places/(\d+|[a-z_]+)/', empty_view, name="places3"),
    url(r'^places/(?P<id>\d+)/$', empty_view, name="places4"),
    url(r'^people/(?P<name>\w+)/$', empty_view, name="people"),
    url(r'^people/(?:name/)', empty_view, name="people2"),
    url(r'^people/(?:name/(\w+)/)?', empty_view, name="people2a"),
    url(r'^people/(?P<name>\w+)-(?P=name)/$', empty_view, name="people_backref"),
    url(r'^optional/(?P<name>.*)/(?:.+/)?', empty_view, name="optional"),
    url(r'^hardcoded/$', empty_view, name="hardcoded"),
    url(r'^hardcoded/doc\.pdf$', empty_view, name="hardcoded2"),
    url(r'^people/(?P<state>\w\w)/(?P<name>\w+)/$', empty_view, name="people3"),
    url(r'^people/(?P<state>\w\w)/(?P<name>\d)/$', empty_view, name="people4"),
    url(r'^people/((?P<state>\w\w)/test)?/(\w+)/$', empty_view, name="people6"),
    url(r'^character_set/[abcdef0-9]/$', empty_view, name="range"),
    url(r'^character_set/[\w]/$', empty_view, name="range2"),
    url(r'^price/\$(\d+)/$', empty_view, name="price"),
    url(r'^price/[$](\d+)/$', empty_view, name="price2"),
    url(r'^price/[\$](\d+)/$', empty_view, name="price3"),
    url(r'^product/(?P<product>\w+)\+\(\$(?P<price>\d+(\.\d+)?)\)/$',
            empty_view, name="product"),
    url(r'^headlines/(?P<year>\d+)\.(?P<month>\d+)\.(?P<day>\d+)/$', empty_view,
            name="headlines"),
    url(r'^windows_path/(?P<drive_name>[A-Z]):\\(?P<path>.+)/$', empty_view,
            name="windows"),
    url(r'^special_chars/(.+)/$', empty_view, name="special"),
    url(r'^(?P<name>.+)/\d+/$', empty_view, name="mixed"),
    url(r'^repeats/a{1,2}/$', empty_view, name="repeats"),
    url(r'^repeats/a{2,4}/$', empty_view, name="repeats2"),
    url(r'^repeats/a{2}/$', empty_view, name="repeats3"),
    url(r'^(?i)CaseInsensitive/(\w+)', empty_view, name="insensitive"),
    url(r'^test/1/?', empty_view, name="test"),
    url(r'^(?i)test/2/?$', empty_view, name="test2"),
    url(r'^outer/(?P<outer>\d+)/',
            include('regressiontests.urlpatterns_reverse.included_urls')),
    url('', include('regressiontests.urlpatterns_reverse.extra_urls')),

    # This is non-reversible, but we shouldn't blow up when parsing it.
    url(r'^(?:foo|bar)(\w+)/$', empty_view, name="disjunction"),

    # Partials should be fine.
    url(r'^partial/', empty_view_partial, name="partial"),
    url(r'^partial_wrapped/', empty_view_wrapped, name="partial_wrapped"),

    # Regression views for #9038. See tests for more details
    url(r'arg_view/$', 'kwargs_view'),
    url(r'arg_view/(?P<arg1>\d+)/$', 'kwargs_view'),
    url(r'absolute_arg_view/(?P<arg1>\d+)/$', absolute_kwargs_view),
    url(r'absolute_arg_view/$', absolute_kwargs_view),

    # Tests for #13154. Mixed syntax to test both ways of defining URLs.
    url(r'defaults_view1/(?P<arg1>\d+)/', 'defaults_view', {'arg2': 1}, name='defaults'),
    (r'defaults_view2/(?P<arg1>\d+)/', 'defaults_view', {'arg2': 2}, 'defaults'),

    url('^includes/', include(other_patterns)),

    # Security tests
    url('(.+)/security/$', empty_view, name='security'),
)
