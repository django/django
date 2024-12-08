from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.urls import path, re_path
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView, dates

from . import views
from .models import Book

urlpatterns = [
    # TemplateView
    path("template/no_template/", TemplateView.as_view()),
    path("template/login_required/", login_required(TemplateView.as_view())),
    path(
        "template/simple/<foo>/",
        TemplateView.as_view(template_name="generic_views/about.html"),
    ),
    path(
        "template/custom/<foo>/",
        views.CustomTemplateView.as_view(template_name="generic_views/about.html"),
    ),
    path(
        "template/content_type/",
        TemplateView.as_view(
            template_name="generic_views/robots.txt", content_type="text/plain"
        ),
    ),
    path(
        "template/cached/<foo>/",
        cache_page(2)(TemplateView.as_view(template_name="generic_views/about.html")),
    ),
    path(
        "template/extra_context/",
        TemplateView.as_view(
            template_name="generic_views/about.html", extra_context={"title": "Title"}
        ),
    ),
    # DetailView
    path("detail/obj/", views.ObjectDetail.as_view()),
    path("detail/artist/<int:pk>/", views.ArtistDetail.as_view(), name="artist_detail"),
    path("detail/author/<int:pk>/", views.AuthorDetail.as_view(), name="author_detail"),
    path(
        "detail/author/bycustompk/<foo>/",
        views.AuthorDetail.as_view(pk_url_kwarg="foo"),
    ),
    path("detail/author/byslug/<slug>/", views.AuthorDetail.as_view()),
    path(
        "detail/author/bycustomslug/<foo>/",
        views.AuthorDetail.as_view(slug_url_kwarg="foo"),
    ),
    path("detail/author/bypkignoreslug/<int:pk>-<slug>/", views.AuthorDetail.as_view()),
    path(
        "detail/author/bypkandslug/<int:pk>-<slug>/",
        views.AuthorDetail.as_view(query_pk_and_slug=True),
    ),
    path(
        "detail/author/<int:pk>/template_name_suffix/",
        views.AuthorDetail.as_view(template_name_suffix="_view"),
    ),
    path(
        "detail/author/<int:pk>/template_name/",
        views.AuthorDetail.as_view(template_name="generic_views/about.html"),
    ),
    path(
        "detail/author/<int:pk>/context_object_name/",
        views.AuthorDetail.as_view(context_object_name="thingy"),
    ),
    path("detail/author/<int:pk>/custom_detail/", views.AuthorCustomDetail.as_view()),
    path(
        "detail/author/<int:pk>/dupe_context_object_name/",
        views.AuthorDetail.as_view(context_object_name="object"),
    ),
    path("detail/page/<int:pk>/field/", views.PageDetail.as_view()),
    path(r"detail/author/invalid/url/", views.AuthorDetail.as_view()),
    path("detail/author/invalid/qs/", views.AuthorDetail.as_view(queryset=None)),
    path("detail/nonmodel/1/", views.NonModelDetail.as_view()),
    path("detail/doesnotexist/<pk>/", views.ObjectDoesNotExistDetail.as_view()),
    # FormView
    path("contact/", views.ContactView.as_view()),
    path("late-validation/", views.LateValidationView.as_view()),
    # Create/UpdateView
    path("edit/artists/create/", views.ArtistCreate.as_view()),
    path("edit/artists/<int:pk>/update/", views.ArtistUpdate.as_view()),
    path("edit/authors/create/naive/", views.NaiveAuthorCreate.as_view()),
    path(
        "edit/authors/create/redirect/",
        views.NaiveAuthorCreate.as_view(success_url="/edit/authors/create/"),
    ),
    path(
        "edit/authors/create/interpolate_redirect/",
        views.NaiveAuthorCreate.as_view(success_url="/edit/author/{id}/update/"),
    ),
    path(
        "edit/authors/create/interpolate_redirect_nonascii/",
        views.NaiveAuthorCreate.as_view(success_url="/%C3%A9dit/author/{id}/update/"),
    ),
    path("edit/authors/create/restricted/", views.AuthorCreateRestricted.as_view()),
    re_path("^[eé]dit/authors/create/$", views.AuthorCreate.as_view()),
    path("edit/authors/create/special/", views.SpecializedAuthorCreate.as_view()),
    path("edit/author/<int:pk>/update/naive/", views.NaiveAuthorUpdate.as_view()),
    path(
        "edit/author/<int:pk>/update/redirect/",
        views.NaiveAuthorUpdate.as_view(success_url="/edit/authors/create/"),
    ),
    path(
        "edit/author/<int:pk>/update/interpolate_redirect/",
        views.NaiveAuthorUpdate.as_view(success_url="/edit/author/{id}/update/"),
    ),
    path(
        "edit/author/<int:pk>/update/interpolate_redirect_nonascii/",
        views.NaiveAuthorUpdate.as_view(success_url="/%C3%A9dit/author/{id}/update/"),
    ),
    re_path("^[eé]dit/author/(?P<pk>[0-9]+)/update/$", views.AuthorUpdate.as_view()),
    path("edit/author/update/", views.OneAuthorUpdate.as_view()),
    path(
        "edit/author/<int:pk>/update/special/", views.SpecializedAuthorUpdate.as_view()
    ),
    path("edit/author/<int:pk>/delete/naive/", views.NaiveAuthorDelete.as_view()),
    path(
        "edit/author/<int:pk>/delete/redirect/",
        views.NaiveAuthorDelete.as_view(success_url="/edit/authors/create/"),
    ),
    path(
        "edit/author/<int:pk>/delete/interpolate_redirect/",
        views.NaiveAuthorDelete.as_view(
            success_url="/edit/authors/create/?deleted={id}"
        ),
    ),
    path(
        "edit/author/<int:pk>/delete/interpolate_redirect_nonascii/",
        views.NaiveAuthorDelete.as_view(
            success_url="/%C3%A9dit/authors/create/?deleted={id}"
        ),
    ),
    path("edit/author/<int:pk>/delete/", views.AuthorDelete.as_view()),
    path(
        "edit/author/<int:pk>/delete/special/", views.SpecializedAuthorDelete.as_view()
    ),
    path("edit/author/<int:pk>/delete/form/", views.AuthorDeleteFormView.as_view()),
    # ArchiveIndexView
    path("dates/books/", views.BookArchive.as_view()),
    path(
        "dates/books/context_object_name/",
        views.BookArchive.as_view(context_object_name="thingies"),
    ),
    path("dates/books/allow_empty/", views.BookArchive.as_view(allow_empty=True)),
    path(
        "dates/books/template_name/",
        views.BookArchive.as_view(template_name="generic_views/list.html"),
    ),
    path(
        "dates/books/template_name_suffix/",
        views.BookArchive.as_view(template_name_suffix="_detail"),
    ),
    path("dates/books/invalid/", views.BookArchive.as_view(queryset=None)),
    path("dates/books/paginated/", views.BookArchive.as_view(paginate_by=10)),
    path(
        "dates/books/reverse/",
        views.BookArchive.as_view(queryset=Book.objects.order_by("pubdate")),
    ),
    path("dates/books/by_month/", views.BookArchive.as_view(date_list_period="month")),
    path("dates/booksignings/", views.BookSigningArchive.as_view()),
    path("dates/books/sortedbyname/", views.BookArchive.as_view(ordering="name")),
    path("dates/books/sortedbynamedec/", views.BookArchive.as_view(ordering="-name")),
    path(
        "dates/books/without_date_field/", views.BookArchiveWithoutDateField.as_view()
    ),
    # ListView
    path("list/dict/", views.DictList.as_view()),
    path("list/dict/paginated/", views.DictList.as_view(paginate_by=1)),
    path("list/artists/", views.ArtistList.as_view(), name="artists_list"),
    path("list/authors/", views.AuthorList.as_view(), name="authors_list"),
    path("list/authors/paginated/", views.AuthorList.as_view(paginate_by=30)),
    path(
        "list/authors/paginated/<int:page>/", views.AuthorList.as_view(paginate_by=30)
    ),
    path(
        "list/authors/paginated-orphaned/",
        views.AuthorList.as_view(paginate_by=30, paginate_orphans=2),
    ),
    path("list/authors/notempty/", views.AuthorList.as_view(allow_empty=False)),
    path(
        "list/authors/notempty/paginated/",
        views.AuthorList.as_view(allow_empty=False, paginate_by=2),
    ),
    path(
        "list/authors/template_name/",
        views.AuthorList.as_view(template_name="generic_views/list.html"),
    ),
    path(
        "list/authors/template_name_suffix/",
        views.AuthorList.as_view(template_name_suffix="_objects"),
    ),
    path(
        "list/authors/context_object_name/",
        views.AuthorList.as_view(context_object_name="author_list"),
    ),
    path(
        "list/authors/dupe_context_object_name/",
        views.AuthorList.as_view(context_object_name="object_list"),
    ),
    path("list/authors/invalid/", views.AuthorList.as_view(queryset=None)),
    path(
        "list/authors/get_queryset/",
        views.AuthorListGetQuerysetReturnsNone.as_view(),
    ),
    path(
        "list/authors/paginated/custom_class/",
        views.AuthorList.as_view(paginate_by=5, paginator_class=views.CustomPaginator),
    ),
    path(
        "list/authors/paginated/custom_page_kwarg/",
        views.AuthorList.as_view(paginate_by=30, page_kwarg="pagina"),
    ),
    path(
        "list/authors/paginated/custom_constructor/",
        views.AuthorListCustomPaginator.as_view(),
    ),
    path("list/books/sorted/", views.BookList.as_view(ordering="name")),
    path(
        "list/books/sortedbypagesandnamedec/",
        views.BookList.as_view(ordering=("pages", "-name")),
    ),
    # YearArchiveView
    # Mixing keyword and positional captures below is intentional; the views
    # ought to be able to accept either.
    path("dates/books/<int:year>/", views.BookYearArchive.as_view()),
    path(
        "dates/books/<int:year>/make_object_list/",
        views.BookYearArchive.as_view(make_object_list=True),
    ),
    path(
        "dates/books/<int:year>/allow_empty/",
        views.BookYearArchive.as_view(allow_empty=True),
    ),
    path(
        "dates/books/<int:year>/allow_future/",
        views.BookYearArchive.as_view(allow_future=True),
    ),
    path(
        "dates/books/<int:year>/paginated/",
        views.BookYearArchive.as_view(make_object_list=True, paginate_by=30),
    ),
    path(
        "dates/books/<int:year>/sortedbyname/",
        views.BookYearArchive.as_view(make_object_list=True, ordering="name"),
    ),
    path(
        "dates/books/<int:year>/sortedbypageandnamedec/",
        views.BookYearArchive.as_view(
            make_object_list=True, ordering=("pages", "-name")
        ),
    ),
    path("dates/books/no_year/", views.BookYearArchive.as_view()),
    path(
        "dates/books/<int:year>/reverse/",
        views.BookYearArchive.as_view(queryset=Book.objects.order_by("pubdate")),
    ),
    path("dates/booksignings/<int:year>/", views.BookSigningYearArchive.as_view()),
    # MonthArchiveView
    path(
        "dates/books/<int:year>/<int:month>/",
        views.BookMonthArchive.as_view(month_format="%m"),
    ),
    path("dates/books/<int:year>/<month>/", views.BookMonthArchive.as_view()),
    path("dates/books/without_month/<int:year>/", views.BookMonthArchive.as_view()),
    path(
        "dates/books/<int:year>/<month>/allow_empty/",
        views.BookMonthArchive.as_view(allow_empty=True),
    ),
    path(
        "dates/books/<int:year>/<month>/allow_future/",
        views.BookMonthArchive.as_view(allow_future=True),
    ),
    path(
        "dates/books/<int:year>/<month>/paginated/",
        views.BookMonthArchive.as_view(paginate_by=30),
    ),
    path("dates/books/<int:year>/no_month/", views.BookMonthArchive.as_view()),
    path(
        "dates/booksignings/<int:year>/<month>/",
        views.BookSigningMonthArchive.as_view(),
    ),
    # WeekArchiveView
    path("dates/books/<int:year>/week/<int:week>/", views.BookWeekArchive.as_view()),
    path(
        "dates/books/<int:year>/week/<int:week>/allow_empty/",
        views.BookWeekArchive.as_view(allow_empty=True),
    ),
    path(
        "dates/books/<int:year>/week/<int:week>/allow_future/",
        views.BookWeekArchive.as_view(allow_future=True),
    ),
    path(
        "dates/books/<int:year>/week/<int:week>/paginated/",
        views.BookWeekArchive.as_view(paginate_by=30),
    ),
    path("dates/books/<int:year>/week/no_week/", views.BookWeekArchive.as_view()),
    path(
        "dates/books/<int:year>/week/<int:week>/monday/",
        views.BookWeekArchive.as_view(week_format="%W"),
    ),
    path(
        "dates/books/<int:year>/week/<int:week>/unknown_week_format/",
        views.BookWeekArchive.as_view(week_format="%T"),
    ),
    path(
        "dates/books/<int:year>/week/<int:week>/iso_format/",
        views.BookWeekArchive.as_view(year_format="%G", week_format="%V"),
    ),
    path(
        "dates/books/<int:year>/week/<int:week>/invalid_iso_week_year_format/",
        views.BookWeekArchive.as_view(week_format="%V"),
    ),
    path(
        "dates/booksignings/<int:year>/week/<int:week>/",
        views.BookSigningWeekArchive.as_view(),
    ),
    # DayArchiveView
    path(
        "dates/books/<int:year>/<int:month>/<int:day>/",
        views.BookDayArchive.as_view(month_format="%m"),
    ),
    path("dates/books/<int:year>/<month>/<int:day>/", views.BookDayArchive.as_view()),
    path(
        "dates/books/<int:year>/<month>/<int:day>/allow_empty/",
        views.BookDayArchive.as_view(allow_empty=True),
    ),
    path(
        "dates/books/<int:year>/<month>/<int:day>/allow_future/",
        views.BookDayArchive.as_view(allow_future=True),
    ),
    path(
        "dates/books/<int:year>/<month>/<int:day>/allow_empty_and_future/",
        views.BookDayArchive.as_view(allow_empty=True, allow_future=True),
    ),
    path(
        "dates/books/<int:year>/<month>/<int:day>/paginated/",
        views.BookDayArchive.as_view(paginate_by=True),
    ),
    path("dates/books/<int:year>/<month>/no_day/", views.BookDayArchive.as_view()),
    path(
        "dates/booksignings/<int:year>/<month>/<int:day>/",
        views.BookSigningDayArchive.as_view(),
    ),
    # TodayArchiveView
    path("dates/books/today/", views.BookTodayArchive.as_view()),
    path(
        "dates/books/today/allow_empty/",
        views.BookTodayArchive.as_view(allow_empty=True),
    ),
    path("dates/booksignings/today/", views.BookSigningTodayArchive.as_view()),
    # DateDetailView
    path(
        "dates/books/<int:year>/<int:month>/<day>/<int:pk>/",
        views.BookDetail.as_view(month_format="%m"),
    ),
    path("dates/books/<int:year>/<month>/<day>/<int:pk>/", views.BookDetail.as_view()),
    path(
        "dates/books/<int:year>/<month>/<int:day>/<int:pk>/allow_future/",
        views.BookDetail.as_view(allow_future=True),
    ),
    path("dates/books/<int:year>/<month>/<int:day>/nopk/", views.BookDetail.as_view()),
    path(
        "dates/books/<int:year>/<month>/<int:day>/byslug/<slug:slug>/",
        views.BookDetail.as_view(),
    ),
    path(
        "dates/books/get_object_custom_queryset/<int:year>/<month>/<int:day>/<int:pk>/",
        views.BookDetailGetObjectCustomQueryset.as_view(),
    ),
    path(
        "dates/booksignings/<int:year>/<month>/<int:day>/<int:pk>/",
        views.BookSigningDetail.as_view(),
    ),
    # Useful for testing redirects
    path("accounts/login/", auth_views.LoginView.as_view()),
    path("BaseDateListViewTest/", dates.BaseDateListView.as_view()),
]
