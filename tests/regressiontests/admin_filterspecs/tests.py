from django.contrib.auth.admin import UserAdmin
from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.utils.encoding import force_unicode

from models import Book, BoolTest, Employee, Department

def select_by(dictlist, key, value):
    return [x for x in dictlist if x[key] == value][0]

class FilterSpecsTests(TestCase):

    def setUp(self):
        # Users
        self.alfred = User.objects.create_user('alfred', 'alfred@example.com')
        self.bob = User.objects.create_user('bob', 'bob@example.com')
        lisa = User.objects.create_user('lisa', 'lisa@example.com')

        #Books
        self.bio_book = Book.objects.create(title='Django: a biography', year=1999, author=self.alfred)
        self.django_book = Book.objects.create(title='The Django Book', year=None, author=self.bob)
        gipsy_book = Book.objects.create(title='Gipsy guitar for dummies', year=2002)
        gipsy_book.contributors = [self.bob, lisa]
        gipsy_book.save()

        # BoolTests
        self.trueTest = BoolTest.objects.create(completed=True)
        self.falseTest = BoolTest.objects.create(completed=False)

        self.request_factory = RequestFactory()

    def get_changelist(self, request, model, modeladmin):
        return ChangeList(request, model, modeladmin.list_display, modeladmin.list_display_links,
            modeladmin.list_filter, modeladmin.date_hierarchy, modeladmin.search_fields,
            modeladmin.list_select_related, modeladmin.list_per_page, modeladmin.list_editable, modeladmin)

    def test_AllValuesFilterSpec(self):
        modeladmin = BookAdmin(Book, admin.site)

        request = self.request_factory.get('/', {'year__isnull': 'True'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure changelist.get_query_set() does not raise IncorrectLookupParameters
        queryset = changelist.get_query_set()

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title()), u'year')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?year__isnull=True')

        request = self.request_factory.get('/', {'year': '2002'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title()), u'year')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[2]['selected'], True)
        self.assertEqual(choices[2]['query_string'], '?year=2002')

    def test_RelatedFilterSpec_ForeignKey(self):
        modeladmin = BookAdmin(Book, admin.site)

        request = self.request_factory.get('/', {'author__isnull': 'True'})
        changelist = ChangeList(request, Book, modeladmin.list_display, modeladmin.list_display_links,
            modeladmin.list_filter, modeladmin.date_hierarchy, modeladmin.search_fields,
            modeladmin.list_select_related, modeladmin.list_per_page, modeladmin.list_editable, modeladmin)

        # Make sure changelist.get_query_set() does not raise IncorrectLookupParameters
        queryset = changelist.get_query_set()

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title()), u'author')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?author__isnull=True')

        request = self.request_factory.get('/', {'author__id__exact': self.alfred.pk})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title()), u'author')
        # order of choices depends on User model, which has no order
        choice = select_by(filterspec.choices(changelist), "display", "alfred")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?author__id__exact=%d' % self.alfred.pk)

    def test_RelatedFilterSpec_ManyToMany(self):
        modeladmin = BookAdmin(Book, admin.site)

        request = self.request_factory.get('/', {'contributors__isnull': 'True'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure changelist.get_query_set() does not raise IncorrectLookupParameters
        queryset = changelist.get_query_set()

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][2]
        self.assertEqual(force_unicode(filterspec.title()), u'user')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?contributors__isnull=True')

        request = self.request_factory.get('/', {'contributors__id__exact': self.bob.pk})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][2]
        self.assertEqual(force_unicode(filterspec.title()), u'user')
        choice = select_by(filterspec.choices(changelist), "display", "bob")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?contributors__id__exact=%d' % self.bob.pk)


    def test_RelatedFilterSpec_reverse_relationships(self):
        modeladmin = CustomUserAdmin(User, admin.site)

        # FK relationship -----
        request = self.request_factory.get('/', {'books_authored__isnull': 'True'})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure changelist.get_query_set() does not raise IncorrectLookupParameters
        queryset = changelist.get_query_set()

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title()), u'book')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?books_authored__isnull=True')

        request = self.request_factory.get('/', {'books_authored__id__exact': self.bio_book.pk})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title()), u'book')
        choice = select_by(filterspec.choices(changelist), "display", self.bio_book.title)
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?books_authored__id__exact=%d' % self.bio_book.pk)

        # M2M relationship -----
        request = self.request_factory.get('/', {'books_contributed__isnull': 'True'})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure changelist.get_query_set() does not raise IncorrectLookupParameters
        queryset = changelist.get_query_set()

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title()), u'book')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], True)
        self.assertEqual(choices[-1]['query_string'], '?books_contributed__isnull=True')

        request = self.request_factory.get('/', {'books_contributed__id__exact': self.django_book.pk})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEqual(force_unicode(filterspec.title()), u'book')
        choice = select_by(filterspec.choices(changelist), "display", self.django_book.title)
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?books_contributed__id__exact=%d' % self.django_book.pk)

    def test_BooleanFilterSpec(self):
        modeladmin = BoolTestAdmin(BoolTest, admin.site)

        request = self.request_factory.get('/')
        changelist = ChangeList(request, BoolTest, modeladmin.list_display, modeladmin.list_display_links,
            modeladmin.list_filter, modeladmin.date_hierarchy, modeladmin.search_fields,
            modeladmin.list_select_related, modeladmin.list_per_page, modeladmin.list_editable, modeladmin)

        # Make sure changelist.get_query_set() does not raise IncorrectLookupParameters
        queryset = changelist.get_query_set()

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title()), u'completed')
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices[-1]['selected'], False)
        self.assertEqual(choices[-1]['query_string'], '?completed__exact=0')

        request = self.request_factory.get('/', {'completed__exact': 1})
        changelist = self.get_changelist(request, BoolTest, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEqual(force_unicode(filterspec.title()), u'completed')
        # order of choices depends on User model, which has no order
        choice = select_by(filterspec.choices(changelist), "display", "Yes")
        self.assertEqual(choice['selected'], True)
        self.assertEqual(choice['query_string'], '?completed__exact=1')

    def test_fk_with_to_field(self):
        """
        Ensure that a filter on a FK respects the FK's to_field attribute.
        Refs #17972.
        """
        modeladmin = EmployeeAdmin(Employee, admin.site)

        dev = Department.objects.create(code='DEV', description='Development')
        design = Department.objects.create(code='DSN', description='Design')
        john = Employee.objects.create(name='John Blue', department=dev)
        jack = Employee.objects.create(name='Jack Red', department=design)

        request = self.request_factory.get('/', {})
        changelist = self.get_changelist(request, Employee, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set()
        self.assertEqual(list(queryset), [jack, john])

        filterspec = changelist.get_filters(request)[0][-1]
        self.assertEqual(force_unicode(filterspec.title()), u'department')
        choices = list(filterspec.choices(changelist))

        self.assertEqual(choices[0]['display'], u'All')
        self.assertEqual(choices[0]['selected'], True)
        self.assertEqual(choices[0]['query_string'], '?')

        self.assertEqual(choices[1]['display'], u'Development')
        self.assertEqual(choices[1]['selected'], False)
        self.assertEqual(choices[1]['query_string'], '?department__code__exact=DEV')

        self.assertEqual(choices[2]['display'], u'Design')
        self.assertEqual(choices[2]['selected'], False)
        self.assertEqual(choices[2]['query_string'], '?department__code__exact=DSN')

        # Filter by Department=='Development' --------------------------------

        request = self.request_factory.get('/', {'department__code__exact': 'DEV'})
        changelist = self.get_changelist(request, Employee, modeladmin)

        # Make sure the correct queryset is returned
        queryset = changelist.get_query_set()
        self.assertEqual(list(queryset), [john])

        filterspec = changelist.get_filters(request)[0][-1]
        self.assertEqual(force_unicode(filterspec.title()), u'department')
        choices = list(filterspec.choices(changelist))

        self.assertEqual(choices[0]['display'], u'All')
        self.assertEqual(choices[0]['selected'], False)
        self.assertEqual(choices[0]['query_string'], '?')

        self.assertEqual(choices[1]['display'], u'Development')
        self.assertEqual(choices[1]['selected'], True)
        self.assertEqual(choices[1]['query_string'], '?department__code__exact=DEV')

        self.assertEqual(choices[2]['display'], u'Design')
        self.assertEqual(choices[2]['selected'], False)
        self.assertEqual(choices[2]['query_string'], '?department__code__exact=DSN')


class CustomUserAdmin(UserAdmin):
    list_filter = ('books_authored', 'books_contributed')

class BookAdmin(admin.ModelAdmin):
    list_filter = ('year', 'author', 'contributors')
    order_by = '-id'

class BoolTestAdmin(admin.ModelAdmin):
    list_filter = ('completed',)

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['name', 'department']
    list_filter = ['department']