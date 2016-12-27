from django.conf.urls import include, url

from .views import (
    absolute_kwargs_view, defaults_view, empty_view, empty_view_nested_partial,
    empty_view_partial, empty_view_wrapped, nested_view,
)

other_patterns = [
    url(r'non_path_include/$', empty_view, name='non_path_include'),
    url(r'nested_path/$', nested_view),
]

urlpatterns = [
    url(r'^places/([0-9]+)/$', empty_view, name='places'),
    url(r'^places?/$', empty_view, name="places?"),
    url(r'^places+/$', empty_view, name="places+"),
    url(r'^places*/$', empty_view, name="places*"),
    url(r'^(?:places/)?$', empty_view, name="places2?"),
    url(r'^(?:places/)+$', empty_view, name="places2+"),
    url(r'^(?:places/)*$', empty_view, name="places2*"),
    url(r'^places/([0-9]+|[a-z_]+)/', empty_view, name="places3"),
    url(r'^places/(?P<id>[0-9]+)/$', empty_view, name="places4"),
    url(r'^people/(?P<name>\w+)/$', empty_view, name="people"),
    url(r'^people/(?:name/)', empty_view, name="people2"),
    url(r'^people/(?:name/(\w+)/)?', empty_view, name="people2a"),
    url(r'^people/(?P<name>\w+)-(?P=name)/$', empty_view, name="people_backref"),
    url(r'^optional/(?P<name>.*)/(?:.+/)?', empty_view, name="optional"),
    url(r'^optional/(?P<arg1>\d+)/(?:(?P<arg2>\d+)/)?', absolute_kwargs_view, name="named_optional"),
    url(r'^optional/(?P<arg1>\d+)/(?:(?P<arg2>\d+)/)?$', absolute_kwargs_view, name="named_optional_terminated"),
    url(r'^nested/noncapture/(?:(?P<p>\w+))$', empty_view, name='nested-noncapture'),
    url(r'^nested/capture/((\w+)/)?$', empty_view, name='nested-capture'),
    url(r'^nested/capture/mixed/((?P<p>\w+))$', empty_view, name='nested-mixedcapture'),
    url(r'^nested/capture/named/(?P<outer>(?P<inner>\w+)/)?$', empty_view, name='nested-namedcapture'),
    url(r'^hardcoded/$', empty_view, name="hardcoded"),
    url(r'^hardcoded/doc\.pdf$', empty_view, name="hardcoded2"),
    url(r'^people/(?P<state>\w\w)/(?P<name>\w+)/$', empty_view, name="people3"),
    url(r'^people/(?P<state>\w\w)/(?P<name>[0-9])/$', empty_view, name="people4"),
    url(r'^people/((?P<state>\w\w)/test)?/(\w+)/$', empty_view, name="people6"),
    url(r'^character_set/[abcdef0-9]/$', empty_view, name="range"),
    url(r'^character_set/[\w]/$', empty_view, name="range2"),
    url(r'^price/\$([0-9]+)/$', empty_view, name="price"),
    url(r'^price/[$]([0-9]+)/$', empty_view, name="price2"),
    url(r'^price/[\$]([0-9]+)/$', empty_view, name="price3"),
    url(r'^product/(?P<product>\w+)\+\(\$(?P<price>[0-9]+(\.[0-9]+)?)\)/$', empty_view, name="product"),
    url(r'^headlines/(?P<year>[0-9]+)\.(?P<month>[0-9]+)\.(?P<day>[0-9]+)/$', empty_view, name="headlines"),
    url(r'^windows_path/(?P<drive_name>[A-Z]):\\(?P<path>.+)/$', empty_view, name="windows"),
    url(r'^special_chars/(?P<chars>.+)/$', empty_view, name="special"),
    url(r'^(?P<name>.+)/[0-9]+/$', empty_view, name="mixed"),
    url(r'^repeats/a{1,2}/$', empty_view, name="repeats"),
    url(r'^repeats/a{2,4}/$', empty_view, name="repeats2"),
    url(r'^repeats/a{2}/$', empty_view, name="repeats3"),
    url(r'^test/1/?', empty_view, name="test"),
    url(r'^outer/(?P<outer>[0-9]+)/', include('urlpatterns_reverse.included_urls')),
    url(r'^outer-no-kwargs/([0-9]+)/', include('urlpatterns_reverse.included_no_kwargs_urls')),
    url('', include('urlpatterns_reverse.extra_urls')),
    url(r'^lookahead-/(?!not-a-city)(?P<city>[^/]+)/$', empty_view, name='lookahead-negative'),
    url(r'^lookahead\+/(?=a-city)(?P<city>[^/]+)/$', empty_view, name='lookahead-positive'),
    url(r'^lookbehind-/(?P<city>[^/]+)(?<!not-a-city)/$', empty_view, name='lookbehind-negative'),
    url(r'^lookbehind\+/(?P<city>[^/]+)(?<=a-city)/$', empty_view, name='lookbehind-positive'),

    # Partials should be fine.
    url(r'^partial/', empty_view_partial, name="partial"),
    url(r'^partial_nested/', empty_view_nested_partial, name="partial_nested"),
    url(r'^partial_wrapped/', empty_view_wrapped, name="partial_wrapped"),

    # This is non-reversible, but we shouldn't blow up when parsing it.
    url(r'^(?:foo|bar)(\w+)/$', empty_view, name="disjunction"),

    url(r'absolute_arg_view/$', absolute_kwargs_view),

    # Tests for #13154. Mixed syntax to test both ways of defining URLs.
    url(r'defaults_view1/(?P<arg1>[0-9]+)/', defaults_view, {'arg2': 1}, name='defaults'),
    url(r'defaults_view2/(?P<arg1>[0-9]+)/', defaults_view, {'arg2': 2}, 'defaults'),

    url('^includes/', include(other_patterns)),

    # Security tests
    url('(.+)/security/$', empty_view, name='security'),
]
