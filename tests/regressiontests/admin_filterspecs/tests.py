from django.contrib.auth.admin import UserAdmin
from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import User
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.utils.encoding import force_unicode

from models import Book

class FilterSpecsTests(TestCase):

    def setUp(self):
        # Users
        alfred = User.objects.create_user('alfred', 'alfred@example.com')
        bob = User.objects.create_user('bob', 'alfred@example.com')
        lisa = User.objects.create_user('lisa', 'lisa@example.com')

        #Books
        bio_book = Book.objects.create(title='Django: a biography', year=1999, author=alfred)
        django_book = Book.objects.create(title='The Django Book', year=None, author=bob)
        gipsy_book = Book.objects.create(title='Gipsy guitar for dummies', year=2002)
        gipsy_book.contributors = [bob, lisa]
        gipsy_book.save()

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
        self.assertEquals(force_unicode(filterspec.title()), u'year')
        choices = list(filterspec.choices(changelist))
        self.assertEquals(choices[-1]['selected'], True)
        self.assertEquals(choices[-1]['query_string'], '?year__isnull=True')

        request = self.request_factory.get('/', {'year': '2002'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEquals(force_unicode(filterspec.title()), u'year')
        choices = list(filterspec.choices(changelist))
        self.assertEquals(choices[2]['selected'], True)
        self.assertEquals(choices[2]['query_string'], '?year=2002')

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
        self.assertEquals(force_unicode(filterspec.title()), u'author')
        choices = list(filterspec.choices(changelist))
        self.assertEquals(choices[-1]['selected'], True)
        self.assertEquals(choices[-1]['query_string'], '?author__isnull=True')

        request = self.request_factory.get('/', {'author__id__exact': '1'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEquals(force_unicode(filterspec.title()), u'author')
        choices = list(filterspec.choices(changelist))
        self.assertEquals(choices[1]['selected'], True)
        self.assertEquals(choices[1]['query_string'], '?author__id__exact=1')

    def test_RelatedFilterSpec_ManyToMany(self):
        modeladmin = BookAdmin(Book, admin.site)

        request = self.request_factory.get('/', {'contributors__isnull': 'True'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure changelist.get_query_set() does not raise IncorrectLookupParameters
        queryset = changelist.get_query_set()

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][2]
        self.assertEquals(force_unicode(filterspec.title()), u'user')
        choices = list(filterspec.choices(changelist))
        self.assertEquals(choices[-1]['selected'], True)
        self.assertEquals(choices[-1]['query_string'], '?contributors__isnull=True')

        request = self.request_factory.get('/', {'contributors__id__exact': '2'})
        changelist = self.get_changelist(request, Book, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][2]
        self.assertEquals(force_unicode(filterspec.title()), u'user')
        choices = list(filterspec.choices(changelist))
        self.assertEquals(choices[2]['selected'], True)
        self.assertEquals(choices[2]['query_string'], '?contributors__id__exact=2')


    def test_RelatedFilterSpec_reverse_relationships(self):
        modeladmin = CustomUserAdmin(User, admin.site)

        # FK relationship -----
        request = self.request_factory.get('/', {'books_authored__isnull': 'True'})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure changelist.get_query_set() does not raise IncorrectLookupParameters
        queryset = changelist.get_query_set()

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEquals(force_unicode(filterspec.title()), u'book')
        choices = list(filterspec.choices(changelist))
        self.assertEquals(choices[-1]['selected'], True)
        self.assertEquals(choices[-1]['query_string'], '?books_authored__isnull=True')

        request = self.request_factory.get('/', {'books_authored__id__exact': '1'})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][0]
        self.assertEquals(force_unicode(filterspec.title()), u'book')
        choices = list(filterspec.choices(changelist))
        self.assertEquals(choices[1]['selected'], True)
        self.assertEquals(choices[1]['query_string'], '?books_authored__id__exact=1')

        # M2M relationship -----
        request = self.request_factory.get('/', {'books_contributed__isnull': 'True'})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure changelist.get_query_set() does not raise IncorrectLookupParameters
        queryset = changelist.get_query_set()

        # Make sure the last choice is None and is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEquals(force_unicode(filterspec.title()), u'book')
        choices = list(filterspec.choices(changelist))
        self.assertEquals(choices[-1]['selected'], True)
        self.assertEquals(choices[-1]['query_string'], '?books_contributed__isnull=True')

        request = self.request_factory.get('/', {'books_contributed__id__exact': '2'})
        changelist = self.get_changelist(request, User, modeladmin)

        # Make sure the correct choice is selected
        filterspec = changelist.get_filters(request)[0][1]
        self.assertEquals(force_unicode(filterspec.title()), u'book')
        choices = list(filterspec.choices(changelist))
        self.assertEquals(choices[2]['selected'], True)
        self.assertEquals(choices[2]['query_string'], '?books_contributed__id__exact=2')

class CustomUserAdmin(UserAdmin):
    list_filter = ('books_authored', 'books_contributed')

class BookAdmin(admin.ModelAdmin):
    list_filter = ('year', 'author', 'contributors')
    order_by = '-id'
