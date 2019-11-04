import datetime
import sys
import unittest

from django.contrib.admin import (
    AllValuesFieldListFilter, BooleanFieldListFilter, ModelAdmin,
    RelatedOnlyFieldListFilter, SimpleListFilter, site,
)
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, TestCase, override_settings

from .models import Book, Bookmark, Department, Employee, TaggedItem


def select_by(dictlist, key, value):
    return [x for x in dictlist if x[key] == value][0]


class DecadeListFilter(SimpleListFilter):

    def lookups(self, request, model_admin):
        return (
            ('the 80s', "the 1980's"),
            ('the 90s', "the 1990's"),
            ('the 00s', "the 2000's"),
            ('other', "other decades"),
        )

    def queryset(self, request, queryset):
        decade = self.value()
        if decade == 'the 80s':
            return queryset.filter(year__gte=1980, year__lte=1989)
        if decade == 'the 90s':
            return queryset.filter(year__gte=1990, year__lte=1999)
        if decade == 'the 00s':
            return queryset.filter(year__gte=2000, year__lte=2009)


class NotNinetiesListFilter(SimpleListFilter):
    title = "Not nineties books"
    parameter_name = "book_year"

    def lookups(self, request, model_admin):
        return (
            ('the 90s', "the 1990's"),
        )

    def queryset(self, request, queryset):
        if self.value() == 'the 90s':
            return queryset.filter(year__gte=1990, year__lte=1999)
        else:
            return queryset.exclude(year__gte=1990, year__lte=1999)


class DecadeListFilterWithTitleAndParameter(DecadeListFilter):
    title = 'publication decade'
    parameter_name = 'publication-decade'


class DecadeListFilterWithoutTitle(DecadeListFilter):
    parameter_name = 'publication-decade'


class DecadeListFilterWithoutParameter(DecadeListFilter):
    title = 'publication decade'


class DecadeListFilterWithNoneReturningLookups(DecadeListFilterWithTitleAndParameter):

    def lookups(self, request, model_admin):
        pass


class DecadeListFilterWithFailingQueryset(DecadeListFilterWithTitleAndParameter):

    def queryset(self, request, queryset):
        raise 1 / 0


class DecadeListFilterWithQuerysetBasedLookups(DecadeListFilterWithTitleAndParameter):

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        if qs.filter(year__gte=1980, year__lte=1989).exists():
            yield ('the 80s', "the 1980's")
        if qs.filter(year__gte=1990, year__lte=1999).exists():
            yield ('the 90s', "the 1990's")
        if qs.filter(year__gte=2000, year__lte=2009).exists():
            yield ('the 00s', "the 2000's")


class DecadeListFilterParameterEndsWith__In(DecadeListFilter):
    title = 'publication decade'
    parameter_name = 'decade__in'  # Ends with '__in"


class DecadeListFilterParameterEndsWith__Isnull(DecadeListFilter):
    title = 'publication decade'
    parameter_name = 'decade__isnull'  # Ends with '__isnull"


class DepartmentListFilterLookupWithNonStringValue(SimpleListFilter):
    title = 'department'
    parameter_name = 'department'

    def lookups(self, request, model_admin):
        return sorted({
            (employee.department.id,  # Intentionally not a string (Refs #19318)
             employee.department.code)
            for employee in model_admin.get_queryset(request).all()
        })

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(department__id=self.value())


class DepartmentListFilterLookupWithUnderscoredParameter(DepartmentListFilterLookupWithNonStringValue):
    parameter_name = 'department__whatever'


class DepartmentListFilterLookupWithDynamicValue(DecadeListFilterWithTitleAndParameter):

    def lookups(self, request, model_admin):
        if self.value() == 'the 80s':
            return (('the 90s', "the 1990's"),)
        elif self.value() == 'the 90s':
            return (('the 80s', "the 1980's"),)
        else:
            return (('the 80s', "the 1980's"), ('the 90s', "the 1990's"),)


class CustomUserAdmin(UserAdmin):
    list_filter = ('books_authored', 'books_contributed')


class BookAdmin(ModelAdmin):
    list_filter = ('year', 'author', 'contributors', 'is_best_seller', 'date_registered', 'no')
    ordering = ('-id',)


class BookAdmin2(ModelAdmin):
    list_filter = ('year', 'author', 'contributors', 'is_best_seller2', 'date_registered', 'no')


class BookAdminWithTupleBooleanFilter(BookAdmin):
    list_filter = (
        'year',
        'author',
        'contributors',
        ('is_best_seller', BooleanFieldListFilter),
        'date_registered',
        'no',
    )


class BookAdminWithUnderscoreLookupAndTuple(BookAdmin):
    list_filter = (
        'year',
        ('author__email', AllValuesFieldListFilter),
        'contributors',
        'is_best_seller',
        'date_registered',
        'no',
    )


class BookAdminWithCustomQueryset(ModelAdmin):

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    list_filter = ('year',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(author=self.user)


class BookAdminRelatedOnlyFilter(ModelAdmin):
    list_filter = (
        'year', 'is_best_seller', 'date_registered', 'no',
        ('author', RelatedOnlyFieldListFilter),
        ('contributors', RelatedOnlyFieldListFilter),
        ('employee__department', RelatedOnlyFieldListFilter),
    )
    ordering = ('-id',)


class DecadeFilterBookAdmin(ModelAdmin):
    list_filter = ('author', DecadeListFilterWithTitleAndParameter)
    ordering = ('-id',)


class NotNinetiesListFilterAdmin(ModelAdmin):
    list_filter = (NotNinetiesListFilter,)


class DecadeFilterBookAdminWithoutTitle(ModelAdmin):
    list_filter = (DecadeListFilterWithoutTitle,)


class DecadeFilterBookAdminWithoutParameter(ModelAdmin):
    list_filter = (DecadeListFilterWithoutParameter,)


class DecadeFilterBookAdminWithNoneReturningLookups(ModelAdmin):
    list_filter = (DecadeListFilterWithNoneReturningLookups,)


class DecadeFilterBookAdminWithFailingQueryset(ModelAdmin):
    list_filter = (DecadeListFilterWithFailingQueryset,)


class DecadeFilterBookAdminWithQuerysetBasedLookups(ModelAdmin):
    list_filter = (DecadeListFilterWithQuerysetBasedLookups,)


class DecadeFilterBookAdminParameterEndsWith__In(ModelAdmin):
    list_filter = (DecadeListFilterParameterEndsWith__In,)


class DecadeFilterBookAdminParameterEndsWith__Isnull(ModelAdmin):
    list_filter = (DecadeListFilterParameterEndsWith__Isnull,)


class EmployeeAdmin(ModelAdmin):
    list_display = ['name', 'department']
    list_filter = ['department']


class DepartmentFilterEmployeeAdmin(EmployeeAdmin):
    list_filter = [DepartmentListFilterLookupWithNonStringValue]


class DepartmentFilterUnderscoredEmployeeAdmin(EmployeeAdmin):
    list_filter = [DepartmentListFilterLookupWithUnderscoredParameter]


class DepartmentFilterDynamicValueBookAdmin(EmployeeAdmin):
    list_filter = [DepartmentListFilterLookupWithDynamicValue]


class BookmarkAdminGenericRelation(ModelAdmin):
    list_filter = ['tags__tag']


class ListFiltersTests(TestCase):
    request_factory = RequestFactory()

    @classmethod
    def setUpTestData(cls):
        cls.today = datetime.date.today()
        cls.tomorrow = cls.today + datetime.timedelta(days=1)
        cls.one_week_ago = cls.today - datetime.timedelta(days=7)
        if cls.today.month == 12:
            cls.next_month = cls.today.replace(year=cls.today.year + 1, month=1, day=1)
        else:
            cls.next_month = cls.today.replace(month=cls.today.month + 1, day=1)
        cls.next_year = cls.today.replace(year=cls.today.year + 1, month=1, day=1)

        # Users
        cls.alfred = User.objects.create_superuser('alfred', 'alfred@example.com', 'password')
        cls.bob = User.objects.create_user('bob', 'bob@example.com')
        cls.lisa = User.objects.create_user('lisa', 'lisa@example.com')

        # Books
        cls.djangonaut_book = Book.objects.create(
            title='Djangonaut: an art of living', year=2009,
            author=cls.alfred, is_best_seller=True, date_registered=cls.today,
            is_best_seller2=True,
        )
        cls.bio_book = Book.objects.create(
            title='Django: a biography', year=1999, author=cls.alfred,
            is_best_seller=False, no=207,
            is_best_seller2=False,
        )
        cls.django_book = Book.objects.create(
            title='The Django Book', year=None, author=cls.bob,
            is_best_seller=None, date_registered=cls.today, no=103,
            is_best_seller2=None,
        )
        cls.guitar_book = Book.objects.create(
            title='Guitar for dummies', year=2002, is_best_seller=True,
            date_registered=cls.one_week_ago,
            is_best_seller2=True,
        )
        cls.guitar_book.contributors.set([cls.bob, cls.lisa])

        # Departments
        cls.dev = Department.objects.create(code='DEV', description='Development')
        cls.design = Department.objects.create(code='DSN', description='Design')

        # Employees
        cls.john = Employee.objects.create(name='John Blue', department=cls.dev)
        cls.jack = Employee.objects.create(name='Jack Red', department=cls.design)

    def test_choicesfieldlistfilter_has_none_choice(self):
        """
        The last choice is for the None value.
        """
        class BookmarkChoicesAdmin(ModelAdmin):
            list_display = ['none_or_null']
            list_filter = ['none_or_null']

        modeladmin = BookmarkChoicesAdmin(Bookmark, site)
        request = self.request_factory.get('/', {})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0][0]
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['display'], 'None')
        self.assertEqual(choices[-1]['query_string'], '?none_or_null__isnull=True')

    def test_datefieldlistfilter(self):
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist(request)

        request = self.request_factory.get('/', {
            'date_registered__gte': self.today,
            'date_registered__lt': self.tomorrow},
        )
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.django_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][4]
        self.assertEqual(filterspec.title, 'date registered')
        choice = select_by(filterspec.choices(changelist), "display", "Today")
        self.assertIs(choice['selected'], True)
        self.assertEqual(
            choice['query_string'],
            '?date_registered__gte=%s&date_registered__lt=%s' % (
                self.today,
                self.tomorrow,
            )
        )

        request = self.request_factory.get('/', {
            'date_registered__gte': self.today.replace(day=1),
            'date_registered__lt': self.next_month},
        )
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        if (self.today.year, self.today.month) == (self.one_week_ago.year, self.one_week_ago.month):
            # In case one week ago is in the same month.
            self.assertEqual(list(queryset), [self.guitar_book, self.django_book, self.djangonaut_book])
        else:
            self.assertEqual(list(queryset), [self.django_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][4]
        self.assertEqual(filterspec.title, 'date registered')
        choice = select_by(filterspec.choices(changelist), "display", "This month")
        self.assertIs(choice['selected'], True)
        self.assertEqual(
            choice['query_string'],
            '?date_registered__gte=%s&date_registered__lt=%s' % (
                self.today.replace(day=1),
                self.next_month,
            )
        )

        request = self.request_factory.get('/', {
            'date_registered__gte': self.today.replace(month=1, day=1),
            'date_registered__lt': self.next_year},
        )
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        if self.today.year == self.one_week_ago.year:
            # In case one week ago is in the same year.
            self.assertEqual(list(queryset), [self.guitar_book, self.django_book, self.djangonaut_book])
        else:
            self.assertEqual(list(queryset), [self.django_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][4]
        self.assertEqual(filterspec.title, 'date registered')
        choice = select_by(filterspec.choices(changelist), "display", "This year")
        self.assertIs(choice['selected'], True)
        self.assertEqual(
            choice['query_string'],
            '?date_registered__gte=%s&date_registered__lt=%s' % (
                self.today.replace(month=1, day=1),
                self.next_year,
            )
        )

        request = self.request_factory.get('/', {
            'date_registered__gte': str(self.one_week_ago),
            'date_registered__lt': str(self.tomorrow),
        })
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.guitar_book, self.django_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][4]
        self.assertEqual(filterspec.title, 'date registered')
        choice = select_by(filterspec.choices(changelist), "display", "Past 7 days")
        self.assertIs(choice['selected'], True)
        self.assertEqual(
            choice['query_string'],
            '?date_registered__gte=%s&date_registered__lt=%s' % (
                str(self.one_week_ago),
                str(self.tomorrow),
            )
        )

        # Null/not null queries
        request = self.request_factory.get('/', {'date_registered__isnull': 'True'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset[0], self.bio_book)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][4]
        self.assertEqual(filterspec.title, 'date registered')
        choice = select_by(filterspec.choices(changelist), 'display', 'No date')
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?date_registered__isnull=True')

        request = self.request_factory.get('/', {'date_registered__isnull': 'False'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(queryset.count(), 3)
        self.assertEqual(list(queryset), [self.guitar_book, self.django_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][4]
        self.assertEqual(filterspec.title, 'date registered')
        choice = select_by(filterspec.choices(changelist), 'display', 'Has date')
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?date_registered__isnull=False')

    @unittest.skipIf(
        sys.platform.startswith('win'),
        "Windows doesn't support setting a timezone that differs from the "
        "system timezone."
    )
    @override_settings(USE_TZ=True)
    def test_datefieldlistfilter_with_time_zone_support(self):
        # Regression for #17830
        self.test_datefieldlistfilter()

    def test_allvaluesfieldlistfilter(self):
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/', {'year__isnull': 'True'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.django_book])

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(filterspec.title, 'year')
        choices = list(filterspec.choices(changelist))
        self.assertIs(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?year__isnull=True')

        request = self.request_factory.get('/', {'year': '2002'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(filterspec.title, 'year')
        choices = list(filterspec.choices(changelist))
        self.assertIs(choices[2]['selected'], True)
        self.assertEqual(choices[2]['query_string'], '?year=2002')

    def test_allvaluesfieldlistfilter_custom_qs(self):
        # Make sure that correct filters are returned with custom querysets
        modeladmin = BookAdminWithCustomQueryset(self.alfred, Book, site)
        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        filterspec = changelist.get_filters(request)[0][0]
        choices = list(filterspec.choices(changelist))
        # Should have 'All', 1999 and 2009 options i.e. the subset of years of
        # books written by alfred (which is the filtering criteria set by
        # BookAdminWithCustomQueryset.get_queryset())
        self.assertEqual(3, len(choices))
        self.assertEqual(choices[0]['query_string'], '?')
        self.assertEqual(choices[1]['query_string'], '?year=1999')
        self.assertEqual(choices[2]['query_string'], '?year=2009')

    def test_relatedfieldlistfilter_foreignkey(self):
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure that all users are present in the author's list filter
        filterspec = changelist.get_filters(request)[0][1]
        expected = [(self.alfred.pk, 'alfred'), (self.bob.pk, 'bob'), (self.lisa.pk, 'lisa')]
        self.assertEqual(sorted(filterspec.lookup_choices), sorted(expected))

        request = self.request_factory.get('/', {'author__isnull': 'True'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.guitar_book])

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(filterspec.title, 'Verbose Author')
        choices = list(filterspec.choices(changelist))
        self.assertIs(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?author__isnull=True')

        request = self.request_factory.get('/', {'author__id__exact': self.alfred.pk})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(filterspec.title, 'Verbose Author')
        # order of choices depends on User model, which has no order
        choice = select_by(filterspec.choices(changelist), "display", "alfred")
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?author__id__exact=%d' % self.alfred.pk)

    def test_relatedfieldlistfilter_foreignkey_ordering(self):
        """RelatedFieldListFilter ordering respects ModelAdmin.ordering."""
        class EmployeeAdminWithOrdering(ModelAdmin):
            ordering = ('name',)

        class BookAdmin(ModelAdmin):
            list_filter = ('employee',)

        site.register(Employee, EmployeeAdminWithOrdering)
        self.addCleanup(lambda: site.unregister(Employee))
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0][0]
        expected = [(self.jack.pk, 'Jack Red'), (self.john.pk, 'John Blue')]
        self.assertEqual(filterspec.lookup_choices, expected)

    def test_relatedfieldlistfilter_foreignkey_ordering_reverse(self):
        class EmployeeAdminWithOrdering(ModelAdmin):
            ordering = ('-name',)

        class BookAdmin(ModelAdmin):
            list_filter = ('employee',)

        site.register(Employee, EmployeeAdminWithOrdering)
        self.addCleanup(lambda: site.unregister(Employee))
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0][0]
        expected = [(self.john.pk, 'John Blue'), (self.jack.pk, 'Jack Red')]
        self.assertEqual(filterspec.lookup_choices, expected)

    def test_relatedfieldlistfilter_foreignkey_default_ordering(self):
        """RelatedFieldListFilter ordering respects Model.ordering."""
        class BookAdmin(ModelAdmin):
            list_filter = ('employee',)

        self.addCleanup(setattr, Employee._meta, 'ordering', Employee._meta.ordering)
        Employee._meta.ordering = ('name',)
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0][0]
        expected = [(self.jack.pk, 'Jack Red'), (self.john.pk, 'John Blue')]
        self.assertEqual(filterspec.lookup_choices, expected)

    def test_relatedfieldlistfilter_manytomany(self):
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure that all users are present in the contrib's list filter
        filterspec = changelist.get_filters(request)[0][2]
        expected = [(self.alfred.pk, 'alfred'), (self.bob.pk, 'bob'), (self.lisa.pk, 'lisa')]
        self.assertEqual(sorted(filterspec.lookup_choices), sorted(expected))

        request = self.request_factory.get('/', {'contributors__isnull': 'True'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.django_book, self.bio_book, self.djangonaut_book])

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][2]
        self.assertEqual(filterspec.title, 'Verbose Contributors')
        choices = list(filterspec.choices(changelist))
        self.assertIs(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?contributors__isnull=True')

        request = self.request_factory.get('/', {'contributors__id__exact': self.bob.pk})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][2]
        self.assertEqual(filterspec.title, 'Verbose Contributors')
        choice = select_by(filterspec.choices(changelist), "display", "bob")
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?contributors__id__exact=%d' % self.bob.pk)

    def test_relatedfieldlistfilter_reverse_relationships(self):
        modeladmin = CustomUserAdmin(User, site)

        # FK relationship -----
        request = self.request_factory.get('/', {'books_authored__isnull': 'True'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.lisa])

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(filterspec.title, 'book')
        choices = list(filterspec.choices(changelist))
        self.assertIs(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?books_authored__isnull=True')

        request = self.request_factory.get('/', {'books_authored__id__exact': self.bio_book.pk})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(filterspec.title, 'book')
        choice = select_by(filterspec.choices(changelist), "display", self.bio_book.title)
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?books_authored__id__exact=%d' % self.bio_book.pk)

        # M2M relationship -----
        request = self.request_factory.get('/', {'books_contributed__isnull': 'True'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.alfred])

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(filterspec.title, 'book')
        choices = list(filterspec.choices(changelist))
        self.assertIs(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?books_contributed__isnull=True')

        request = self.request_factory.get('/', {'books_contributed__id__exact': self.django_book.pk})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(filterspec.title, 'book')
        choice = select_by(filterspec.choices(changelist), "display", self.django_book.title)
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?books_contributed__id__exact=%d' % self.django_book.pk)

        # With one book, the list filter should appear because there is also a
        # (None) option.
        Book.objects.exclude(pk=self.djangonaut_book.pk).delete()
        filterspec = changelist.get_filters(request)[0]
        self.assertEqual(len(filterspec), 2)
        # With no books remaining, no list filters should appear.
        Book.objects.all().delete()
        filterspec = changelist.get_filters(request)[0]
        self.assertEqual(len(filterspec), 0)

    def test_relatedfieldlistfilter_reverse_relationships_default_ordering(self):
        self.addCleanup(setattr, Book._meta, 'ordering', Book._meta.ordering)
        Book._meta.ordering = ('title',)
        modeladmin = CustomUserAdmin(User, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0][0]
        expected = [
            (self.bio_book.pk, 'Django: a biography'),
            (self.djangonaut_book.pk, 'Djangonaut: an art of living'),
            (self.guitar_book.pk, 'Guitar for dummies'),
            (self.django_book.pk, 'The Django Book')
        ]
        self.assertEqual(filterspec.lookup_choices, expected)

    def test_relatedonlyfieldlistfilter_foreignkey(self):
        modeladmin = BookAdminRelatedOnlyFilter(Book, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure that only actual authors are present in author's list filter
        filterspec = changelist.get_filters(request)[0][4]
        expected = [(self.alfred.pk, 'alfred'), (self.bob.pk, 'bob')]
        self.assertEqual(sorted(filterspec.lookup_choices), sorted(expected))

    def test_relatedonlyfieldlistfilter_foreignkey_default_ordering(self):
        """RelatedOnlyFieldListFilter ordering respects Meta.ordering."""
        class BookAdmin(ModelAdmin):
            list_filter = (
                ('employee', RelatedOnlyFieldListFilter),
            )

        albert = Employee.objects.create(name='Albert Green', department=self.dev)
        self.djangonaut_book.employee = albert
        self.djangonaut_book.save()
        self.bio_book.employee = self.jack
        self.bio_book.save()

        self.addCleanup(setattr, Employee._meta, 'ordering', Employee._meta.ordering)
        Employee._meta.ordering = ('name',)
        modeladmin = BookAdmin(Book, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0][0]
        expected = [(albert.pk, 'Albert Green'), (self.jack.pk, 'Jack Red')]
        self.assertEqual(filterspec.lookup_choices, expected)

    def test_relatedonlyfieldlistfilter_underscorelookup_foreignkey(self):
        Department.objects.create(code='TEST', description='Testing')
        self.djangonaut_book.employee = self.john
        self.djangonaut_book.save()
        self.bio_book.employee = self.jack
        self.bio_book.save()

        modeladmin = BookAdminRelatedOnlyFilter(Book, site)
        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Only actual departments should be present in employee__department's
        # list filter.
        filterspec = changelist.get_filters(request)[0][6]
        expected = [
            (self.dev.code, str(self.dev)),
            (self.design.code, str(self.design)),
        ]
        self.assertEqual(sorted(filterspec.lookup_choices), sorted(expected))

    def test_relatedonlyfieldlistfilter_manytomany(self):
        modeladmin = BookAdminRelatedOnlyFilter(Book, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure that only actual contributors are present in contrib's list filter
        filterspec = changelist.get_filters(request)[0][5]
        expected = [(self.bob.pk, 'bob'), (self.lisa.pk, 'lisa')]
        self.assertEqual(sorted(filterspec.lookup_choices), sorted(expected))

    def test_listfilter_genericrelation(self):
        django_bookmark = Bookmark.objects.create(url='https://www.djangoproject.com/')
        python_bookmark = Bookmark.objects.create(url='https://www.python.org/')
        kernel_bookmark = Bookmark.objects.create(url='https://www.kernel.org/')

        TaggedItem.objects.create(content_object=django_bookmark, tag='python')
        TaggedItem.objects.create(content_object=python_bookmark, tag='python')
        TaggedItem.objects.create(content_object=kernel_bookmark, tag='linux')

        modeladmin = BookmarkAdminGenericRelation(Bookmark, site)

        request = self.request_factory.get('/', {'tags__tag': 'python'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)
        queryset = changelist.get_queryset(request)

        expected = [python_bookmark, django_bookmark]
        self.assertEqual(list(queryset), expected)

    def test_booleanfieldlistfilter(self):
        modeladmin = BookAdmin(Book, site)
        self.verify_booleanfieldlistfilter(modeladmin)

    def test_booleanfieldlistfilter_tuple(self):
        modeladmin = BookAdminWithTupleBooleanFilter(Book, site)
        self.verify_booleanfieldlistfilter(modeladmin)

    def verify_booleanfieldlistfilter(self, modeladmin):
        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        request = self.request_factory.get('/', {'is_best_seller__exact': 0})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.bio_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][3]
        self.assertEqual(filterspec.title, 'is best seller')
        choice = select_by(filterspec.choices(changelist), "display", "No")
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?is_best_seller__exact=0')

        request = self.request_factory.get('/', {'is_best_seller__exact': 1})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.guitar_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][3]
        self.assertEqual(filterspec.title, 'is best seller')
        choice = select_by(filterspec.choices(changelist), "display", "Yes")
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?is_best_seller__exact=1')

        request = self.request_factory.get('/', {'is_best_seller__isnull': 'True'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.django_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][3]
        self.assertEqual(filterspec.title, 'is best seller')
        choice = select_by(filterspec.choices(changelist), "display", "Unknown")
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?is_best_seller__isnull=True')

    def test_booleanfieldlistfilter_nullbooleanfield(self):
        modeladmin = BookAdmin2(Book, site)

        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        request = self.request_factory.get('/', {'is_best_seller2__exact': 0})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.bio_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][3]
        self.assertEqual(filterspec.title, 'is best seller2')
        choice = select_by(filterspec.choices(changelist), "display", "No")
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?is_best_seller2__exact=0')

        request = self.request_factory.get('/', {'is_best_seller2__exact': 1})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.guitar_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][3]
        self.assertEqual(filterspec.title, 'is best seller2')
        choice = select_by(filterspec.choices(changelist), "display", "Yes")
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?is_best_seller2__exact=1')

        request = self.request_factory.get('/', {'is_best_seller2__isnull': 'True'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.django_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][3]
        self.assertEqual(filterspec.title, 'is best seller2')
        choice = select_by(filterspec.choices(changelist), "display", "Unknown")
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?is_best_seller2__isnull=True')

    def test_fieldlistfilter_underscorelookup_tuple(self):
        """
        Ensure ('fieldpath', ClassName ) lookups pass lookup_allowed checks
        when fieldpath contains double underscore in value (#19182).
        """
        modeladmin = BookAdminWithUnderscoreLookupAndTuple(Book, site)
        request = self.request_factory.get('/')
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        request = self.request_factory.get('/', {'author__email': 'alfred@example.com'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.bio_book, self.djangonaut_book])

    def test_fieldlistfilter_invalid_lookup_parameters(self):
        """Filtering by an invalid value."""
        modeladmin = BookAdmin(Book, site)
        request = self.request_factory.get('/', {'author__id__exact': 'StringNotInteger!'})
        request.user = self.alfred
        with self.assertRaises(IncorrectLookupParameters):
            modeladmin.get_changelist_instance(request)

    def test_simplelistfilter(self):
        modeladmin = DecadeFilterBookAdmin(Book, site)

        # Make sure that the first option is 'All' ---------------------------
        request = self.request_factory.get('/', {})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), list(Book.objects.all().order_by('-id')))

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(filterspec.title, 'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[0]['display'], 'All')
        self.assertIs(choices[0]['selected'], True)
        self.assertEqual(choices[0]['query_string'], '?')

        # Look for books in the 1980s ----------------------------------------
        request = self.request_factory.get('/', {'publication-decade': 'the 80s'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(filterspec.title, 'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[1]['display'], 'the 1980\'s')
        self.assertIs(choices[1]['selected'], True)
        self.assertEqual(choices[1]['query_string'], '?publication-decade=the+80s')

        # Look for books in the 1990s ----------------------------------------
        request = self.request_factory.get('/', {'publication-decade': 'the 90s'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.bio_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(filterspec.title, 'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[2]['display'], 'the 1990\'s')
        self.assertIs(choices[2]['selected'], True)
        self.assertEqual(choices[2]['query_string'], '?publication-decade=the+90s')

        # Look for books in the 2000s ----------------------------------------
        request = self.request_factory.get('/', {'publication-decade': 'the 00s'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.guitar_book, self.djangonaut_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(filterspec.title, 'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[3]['display'], 'the 2000\'s')
        self.assertIs(choices[3]['selected'], True)
        self.assertEqual(choices[3]['query_string'], '?publication-decade=the+00s')

        # Combine multiple filters -------------------------------------------
        request = self.request_factory.get('/', {'publication-decade': 'the 00s', 'author__id__exact': self.alfred.pk})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.djangonaut_book])

        # Make sure the correct choices are selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(filterspec.title, 'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[3]['display'], 'the 2000\'s')
        self.assertIs(choices[3]['selected'], True)
        self.assertEqual(
            choices[3]['query_string'],
            '?author__id__exact=%s&publication-decade=the+00s' % self.alfred.pk
        )

        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(filterspec.title, 'Verbose Author')
        choice = select_by(filterspec.choices(changelist), "display", "alfred")
        self.assertIs(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?author__id__exact=%s&publication-decade=the+00s' % self.alfred.pk)

    def test_listfilter_without_title(self):
        """
        Any filter must define a title.
        """
        modeladmin = DecadeFilterBookAdminWithoutTitle(Book, site)
        request = self.request_factory.get('/', {})
        request.user = self.alfred
        msg = "The list filter 'DecadeListFilterWithoutTitle' does not specify a 'title'."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            modeladmin.get_changelist_instance(request)

    def test_simplelistfilter_without_parameter(self):
        """
        Any SimpleListFilter must define a parameter_name.
        """
        modeladmin = DecadeFilterBookAdminWithoutParameter(Book, site)
        request = self.request_factory.get('/', {})
        request.user = self.alfred
        msg = "The list filter 'DecadeListFilterWithoutParameter' does not specify a 'parameter_name'."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            modeladmin.get_changelist_instance(request)

    def test_simplelistfilter_with_none_returning_lookups(self):
        """
        A SimpleListFilter lookups method can return None but disables the
        filter completely.
        """
        modeladmin = DecadeFilterBookAdminWithNoneReturningLookups(Book, site)
        request = self.request_factory.get('/', {})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0]
        self.assertEqual(len(filterspec), 0)

    def test_filter_with_failing_queryset(self):
        """
        When a filter's queryset method fails, it fails loudly and
        the corresponding exception doesn't get swallowed (#17828).
        """
        modeladmin = DecadeFilterBookAdminWithFailingQueryset(Book, site)
        request = self.request_factory.get('/', {})
        request.user = self.alfred
        with self.assertRaises(ZeroDivisionError):
            modeladmin.get_changelist_instance(request)

    def test_simplelistfilter_with_queryset_based_lookups(self):
        modeladmin = DecadeFilterBookAdminWithQuerysetBasedLookups(Book, site)
        request = self.request_factory.get('/', {})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(filterspec.title, 'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(len(choices), 3)

        self.assertEqual(choices[0]['display'], 'All')
        self.assertIs(choices[0]['selected'], True)
        self.assertEqual(choices[0]['query_string'], '?')

        self.assertEqual(choices[1]['display'], 'the 1990\'s')
        self.assertIs(choices[1]['selected'], False)
        self.assertEqual(choices[1]['query_string'], '?publication-decade=the+90s')

        self.assertEqual(choices[2]['display'], 'the 2000\'s')
        self.assertIs(choices[2]['selected'], False)
        self.assertEqual(choices[2]['query_string'], '?publication-decade=the+00s')

    def test_two_characters_long_field(self):
        """
        list_filter works with two-characters long field names (#16080).
        """
        modeladmin = BookAdmin(Book, site)
        request = self.request_factory.get('/', {'no': '207'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.bio_book])

        filterspec = changelist.get_filters(request)[0][-1]
        self.assertEqual(filterspec.title, 'number')
        choices = list(filterspec.choices(changelist))
        self.assertIs(choices[2]['selected'], True)
        self.assertEqual(choices[2]['query_string'], '?no=207')

    def test_parameter_ends_with__in__or__isnull(self):
        """
        A SimpleListFilter's parameter name is not mistaken for a model field
        if it ends with '__isnull' or '__in' (#17091).
        """
        # When it ends with '__in' -----------------------------------------
        modeladmin = DecadeFilterBookAdminParameterEndsWith__In(Book, site)
        request = self.request_factory.get('/', {'decade__in': 'the 90s'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.bio_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(filterspec.title, 'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[2]['display'], 'the 1990\'s')
        self.assertIs(choices[2]['selected'], True)
        self.assertEqual(choices[2]['query_string'], '?decade__in=the+90s')

        # When it ends with '__isnull' ---------------------------------------
        modeladmin = DecadeFilterBookAdminParameterEndsWith__Isnull(Book, site)
        request = self.request_factory.get('/', {'decade__isnull': 'the 90s'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.bio_book])

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(filterspec.title, 'publication decade')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[2]['display'], 'the 1990\'s')
        self.assertIs(choices[2]['selected'], True)
        self.assertEqual(choices[2]['query_string'], '?decade__isnull=the+90s')

    def test_lookup_with_non_string_value(self):
        """
        Ensure choices are set the selected class when using non-string values
        for lookups in SimpleListFilters (#19318).
        """
        modeladmin = DepartmentFilterEmployeeAdmin(Employee, site)
        request = self.request_factory.get('/', {'department': self.john.department.pk})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        queryset = changelist.get_queryset(request)

        self.assertEqual(list(queryset), [self.john])

        filterspec = changelist.get_filters(request)[0][-1]
        self.assertEqual(filterspec.title, 'department')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[1]['display'], 'DEV')
        self.assertIs(choices[1]['selected'], True)
        self.assertEqual(choices[1]['query_string'], '?department=%s' % self.john.department.pk)

    def test_lookup_with_non_string_value_underscored(self):
        """
        Ensure SimpleListFilter lookups pass lookup_allowed checks when
        parameter_name attribute contains double-underscore value (#19182).
        """
        modeladmin = DepartmentFilterUnderscoredEmployeeAdmin(Employee, site)
        request = self.request_factory.get('/', {'department__whatever': self.john.department.pk})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        queryset = changelist.get_queryset(request)

        self.assertEqual(list(queryset), [self.john])

        filterspec = changelist.get_filters(request)[0][-1]
        self.assertEqual(filterspec.title, 'department')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[1]['display'], 'DEV')
        self.assertIs(choices[1]['selected'], True)
        self.assertEqual(choices[1]['query_string'], '?department__whatever=%s' % self.john.department.pk)

    def test_fk_with_to_field(self):
        """
        A filter on a FK respects the FK's to_field attribute (#17972).
        """
        modeladmin = EmployeeAdmin(Employee, site)

        request = self.request_factory.get('/', {})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.jack, self.john])

        filterspec = changelist.get_filters(request)[0][-1]
        self.assertEqual(filterspec.title, 'department')
        choices = list(filterspec.choices(changelist))

        self.assertEqual(choices[0]['display'], 'All')
        self.assertIs(choices[0]['selected'], True)
        self.assertEqual(choices[0]['query_string'], '?')

        self.assertEqual(choices[1]['display'], 'Development')
        self.assertIs(choices[1]['selected'], False)
        self.assertEqual(choices[1]['query_string'], '?department__code__exact=DEV')

        self.assertEqual(choices[2]['display'], 'Design')
        self.assertIs(choices[2]['selected'], False)
        self.assertEqual(choices[2]['query_string'], '?department__code__exact=DSN')

        # Filter by Department=='Development' --------------------------------

        request = self.request_factory.get('/', {'department__code__exact': 'DEV'})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)

        # Make sure the correct queryset is returned
        queryset = changelist.get_queryset(request)
        self.assertEqual(list(queryset), [self.john])

        filterspec = changelist.get_filters(request)[0][-1]
        self.assertEqual(filterspec.title, 'department')
        choices = list(filterspec.choices(changelist))

        self.assertEqual(choices[0]['display'], 'All')
        self.assertIs(choices[0]['selected'], False)
        self.assertEqual(choices[0]['query_string'], '?')

        self.assertEqual(choices[1]['display'], 'Development')
        self.assertIs(choices[1]['selected'], True)
        self.assertEqual(choices[1]['query_string'], '?department__code__exact=DEV')

        self.assertEqual(choices[2]['display'], 'Design')
        self.assertIs(choices[2]['selected'], False)
        self.assertEqual(choices[2]['query_string'], '?department__code__exact=DSN')

    def test_lookup_with_dynamic_value(self):
        """
        Ensure SimpleListFilter can access self.value() inside the lookup.
        """
        modeladmin = DepartmentFilterDynamicValueBookAdmin(Book, site)

        def _test_choices(request, expected_displays):
            request.user = self.alfred
            changelist = modeladmin.get_changelist_instance(request)
            filterspec = changelist.get_filters(request)[0][0]
            self.assertEqual(filterspec.title, 'publication decade')
            choices = tuple(c['display'] for c in filterspec.choices(changelist))
            self.assertEqual(choices, expected_displays)

        _test_choices(self.request_factory.get('/', {}),
                      ("All", "the 1980's", "the 1990's"))

        _test_choices(self.request_factory.get('/', {'publication-decade': 'the 80s'}),
                      ("All", "the 1990's"))

        _test_choices(self.request_factory.get('/', {'publication-decade': 'the 90s'}),
                      ("All", "the 1980's"))

    def test_list_filter_queryset_filtered_by_default(self):
        """
        A list filter that filters the queryset by default gives the correct
        full_result_count.
        """
        modeladmin = NotNinetiesListFilterAdmin(Book, site)
        request = self.request_factory.get('/', {})
        request.user = self.alfred
        changelist = modeladmin.get_changelist_instance(request)
        changelist.get_results(request)
        self.assertEqual(changelist.full_result_count, 4)
