from django.urls import include, path, re_path

from .views import (
    absolute_kwargs_view,
    defaults_view,
    empty_view,
    empty_view_nested_partial,
    empty_view_partial,
    empty_view_wrapped,
    nested_view,
    view_func_from_cbv,
)

other_patterns = [
    path("non_path_include/", empty_view, name="non_path_include"),
    path("nested_path/", nested_view),
]

urlpatterns = [
    re_path(r"^places/([0-9]+)/$", empty_view, name="places"),
    re_path(r"^places?/$", empty_view, name="places?"),
    re_path(r"^places+/$", empty_view, name="places+"),
    re_path(r"^places*/$", empty_view, name="places*"),
    re_path(r"^(?:places/)?$", empty_view, name="places2?"),
    re_path(r"^(?:places/)+$", empty_view, name="places2+"),
    re_path(r"^(?:places/)*$", empty_view, name="places2*"),
    re_path(r"^places/([0-9]+|[a-z_]+)/", empty_view, name="places3"),
    re_path(r"^places/(?P<id>[0-9]+)/$", empty_view, name="places4"),
    re_path(r"^people/(?P<name>\w+)/$", empty_view, name="people"),
    re_path(r"^people/(?:name/)$", empty_view, name="people2"),
    re_path(r"^people/(?:name/(\w+)/)?$", empty_view, name="people2a"),
    re_path(r"^people/(?P<name>\w+)-(?P=name)/$", empty_view, name="people_backref"),
    re_path(r"^optional/(?P<name>.*)/(?:.+/)?", empty_view, name="optional"),
    re_path(
        r"^optional/(?P<arg1>\d+)/(?:(?P<arg2>\d+)/)?",
        absolute_kwargs_view,
        name="named_optional",
    ),
    re_path(
        r"^optional/(?P<arg1>\d+)/(?:(?P<arg2>\d+)/)?$",
        absolute_kwargs_view,
        name="named_optional_terminated",
    ),
    re_path(
        r"^nested/noncapture/(?:(?P<p>\w+))$", empty_view, name="nested-noncapture"
    ),
    re_path(r"^nested/capture/((\w+)/)?$", empty_view, name="nested-capture"),
    re_path(
        r"^nested/capture/mixed/((?P<p>\w+))$", empty_view, name="nested-mixedcapture"
    ),
    re_path(
        r"^nested/capture/named/(?P<outer>(?P<inner>\w+)/)?$",
        empty_view,
        name="nested-namedcapture",
    ),
    re_path(r"^hardcoded/$", empty_view, name="hardcoded"),
    re_path(r"^hardcoded/doc\.pdf$", empty_view, name="hardcoded2"),
    re_path(r"^people/(?P<state>\w\w)/(?P<name>\w+)/$", empty_view, name="people3"),
    re_path(r"^people/(?P<state>\w\w)/(?P<name>[0-9])/$", empty_view, name="people4"),
    re_path(r"^people/((?P<state>\w\w)/test)?/(\w+)/$", empty_view, name="people6"),
    re_path(r"^character_set/[abcdef0-9]/$", empty_view, name="range"),
    re_path(r"^character_set/[\w]/$", empty_view, name="range2"),
    re_path(r"^price/\$([0-9]+)/$", empty_view, name="price"),
    re_path(r"^price/[$]([0-9]+)/$", empty_view, name="price2"),
    re_path(r"^price/[\$]([0-9]+)/$", empty_view, name="price3"),
    re_path(
        r"^product/(?P<product>\w+)\+\(\$(?P<price>[0-9]+(\.[0-9]+)?)\)/$",
        empty_view,
        name="product",
    ),
    re_path(
        r"^headlines/(?P<year>[0-9]+)\.(?P<month>[0-9]+)\.(?P<day>[0-9]+)/$",
        empty_view,
        name="headlines",
    ),
    re_path(
        r"^windows_path/(?P<drive_name>[A-Z]):\\(?P<path>.+)/$",
        empty_view,
        name="windows",
    ),
    re_path(r"^special_chars/(?P<chars>.+)/$", empty_view, name="special"),
    re_path(r"^resolved/(?P<arg>\d+)/$", empty_view, {"extra": True}, name="resolved"),
    re_path(
        r"^resolved-overridden/(?P<arg>\d+)/(?P<overridden>\w+)/$",
        empty_view,
        {"extra": True, "overridden": "default"},
        name="resolved-overridden",
    ),
    re_path(r"^(?P<name>.+)/[0-9]+/$", empty_view, name="mixed"),
    re_path(r"^repeats/a{1,2}/$", empty_view, name="repeats"),
    re_path(r"^repeats/a{2,4}/$", empty_view, name="repeats2"),
    re_path(r"^repeats/a{2}/$", empty_view, name="repeats3"),
    re_path(r"^test/1/?", empty_view, name="test"),
    re_path(r"^outer/(?P<outer>[0-9]+)/", include("urlpatterns_reverse.included_urls")),
    re_path(
        r"^outer-no-kwargs/([0-9]+)/",
        include("urlpatterns_reverse.included_no_kwargs_urls"),
    ),
    re_path("", include("urlpatterns_reverse.extra_urls")),
    re_path(
        r"^lookahead-/(?!not-a-city)(?P<city>[^/]+)/$",
        empty_view,
        name="lookahead-negative",
    ),
    re_path(
        r"^lookahead\+/(?=a-city)(?P<city>[^/]+)/$",
        empty_view,
        name="lookahead-positive",
    ),
    re_path(
        r"^lookbehind-/(?P<city>[^/]+)(?<!not-a-city)/$",
        empty_view,
        name="lookbehind-negative",
    ),
    re_path(
        r"^lookbehind\+/(?P<city>[^/]+)(?<=a-city)/$",
        empty_view,
        name="lookbehind-positive",
    ),
    # Partials should be fine.
    path("partial/", empty_view_partial, name="partial"),
    path("partial_nested/", empty_view_nested_partial, name="partial_nested"),
    path("partial_wrapped/", empty_view_wrapped, name="partial_wrapped"),
    # This is non-reversible, but we shouldn't blow up when parsing it.
    re_path(r"^(?:foo|bar)(\w+)/$", empty_view, name="disjunction"),
    path("absolute_arg_view/", absolute_kwargs_view),
    # Tests for #13154. Mixed syntax to test both ways of defining URLs.
    re_path(
        r"^defaults_view1/(?P<arg1>[0-9]+)/$",
        defaults_view,
        {"arg2": 1},
        name="defaults",
    ),
    re_path(
        r"^defaults_view2/(?P<arg1>[0-9]+)/$", defaults_view, {"arg2": 2}, "defaults"
    ),
    path("includes/", include(other_patterns)),
    # Security tests
    re_path("(.+)/security/$", empty_view, name="security"),
    # View function from cbv.
    path("hello/<slug:name>/", view_func_from_cbv),
]
