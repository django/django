from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.views.main import ChangeList, SEARCH_VAR
from django.core.paginator import Paginator
from django.template import Context, Template
from django.test import TransactionTestCase

from models import (Child, Parent, Genre, Band, Musician, Group, Quartet,
    Membership, ChordsMusician, ChordsBand, Invitation)


class ChangeListTests(TransactionTestCase):
    def test_select_related_preserved(self):
        """
        Regression test for #10348: ChangeList.get_query_set() shouldn't
        overwrite a custom select_related provided by ModelAdmin.queryset().
        """
        m = ChildAdmin(Child, admin.site)
        cl = ChangeList(MockRequest(), Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_editable, m)
        self.assertEqual(cl.query_set.query.select_related, {'parent': {'name': {}}})

    def test_result_list_empty_changelist_value(self):
        """
        Regression test for #14982: EMPTY_CHANGELIST_VALUE should be honored
        for relationship fields
        """
        new_child = Child.objects.create(name='name', parent=None)
        request = MockRequest()
        m = ChildAdmin(Child, admin.site)
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_editable, m)
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        row_html = '<tbody><tr class="row1"><td class="action-checkbox"><input type="checkbox" class="action-select" value="%d" name="_selected_action" /></td><th><a href="%d/">name</a></th><td class="nowrap">(None)</td></tr></tbody>' % (new_child.id, new_child.id)
        self.assertFalse(table_output.find(row_html) == -1,
            'Failed to find expected row element: %s' % table_output)


    def test_result_list_html(self):
        """
        Verifies that inclusion tag result_list generates a table when with
        default ModelAdmin settings.
        """
        new_parent = Parent.objects.create(name='parent')
        new_child = Child.objects.create(name='name', parent=new_parent)
        request = MockRequest()
        m = ChildAdmin(Child, admin.site)
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_editable, m)
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        row_html = '<tbody><tr class="row1"><td class="action-checkbox"><input type="checkbox" class="action-select" value="%d" name="_selected_action" /></td><th><a href="%d/">name</a></th><td class="nowrap">Parent object</td></tr></tbody>' % (new_child.id, new_child.id)
        self.assertFalse(table_output.find(row_html) == -1,
            'Failed to find expected row element: %s' % table_output)

    def test_result_list_editable_html(self):
        """
        Regression tests for #11791: Inclusion tag result_list generates a
        table and this checks that the items are nested within the table
        element tags.
        Also a regression test for #13599, verifies that hidden fields
        when list_editable is enabled are rendered in a div outside the
        table.
        """
        new_parent = Parent.objects.create(name='parent')
        new_child = Child.objects.create(name='name', parent=new_parent)
        request = MockRequest()
        m = ChildAdmin(Child, admin.site)

        # Test with list_editable fields
        m.list_display = ['id', 'name', 'parent']
        m.list_display_links = ['id']
        m.list_editable = ['name']
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_editable, m)
        FormSet = m.get_changelist_formset(request)
        cl.formset = FormSet(queryset=cl.result_list)
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        # make sure that hidden fields are in the correct place
        hiddenfields_div = '<div class="hiddenfields"><input type="hidden" name="form-0-id" value="%d" id="id_form-0-id" /></div>' % new_child.id
        self.assertFalse(table_output.find(hiddenfields_div) == -1,
            'Failed to find hidden fields in: %s' % table_output)
        # make sure that list editable fields are rendered in divs correctly
        editable_name_field = '<input name="form-0-name" value="name" class="vTextField" maxlength="30" type="text" id="id_form-0-name" />'
        self.assertFalse('<td>%s</td>' % editable_name_field == -1,
            'Failed to find "name" list_editable field in: %s' % table_output)

    def test_result_list_editable(self):
        """
        Regression test for #14312: list_editable with pagination
        """

        new_parent = Parent.objects.create(name='parent')
        for i in range(200):
            new_child = Child.objects.create(name='name %s' % i, parent=new_parent)
        request = MockRequest()
        request.GET['p'] = -1 # Anything outside range
        m = ChildAdmin(Child, admin.site)

        # Test with list_editable fields
        m.list_display = ['id', 'name', 'parent']
        m.list_display_links = ['id']
        m.list_editable = ['name']
        self.assertRaises(IncorrectLookupParameters, lambda: \
            ChangeList(request, Child, m.list_display, m.list_display_links,
                    m.list_filter, m.date_hierarchy, m.search_fields,
                    m.list_select_related, m.list_per_page, m.list_editable, m))

    def test_custom_paginator(self):
        new_parent = Parent.objects.create(name='parent')
        for i in range(200):
            new_child = Child.objects.create(name='name %s' % i, parent=new_parent)

        request = MockRequest()
        m = ChildAdmin(Child, admin.site)
        m.list_display = ['id', 'name', 'parent']
        m.list_display_links = ['id']
        m.list_editable = ['name']
        m.paginator = CustomPaginator

        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_editable, m)

        cl.get_results(request)
        self.assertIsInstance(cl.paginator, CustomPaginator)

    def test_distinct_for_m2m_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't apper more than once. Basic ManyToMany.
        """
        blues = Genre.objects.create(name='Blues')
        band = Band.objects.create(name='B.B. King Review', nr_of_members=11)

        band.genres.add(blues)
        band.genres.add(blues)

        m = BandAdmin(Band, admin.site)
        request = MockFilterRequest('genres', blues.pk)

        cl = ChangeList(request, Band, m.list_display,
                m.list_display_links, m.list_filter, m.date_hierarchy,
                m.search_fields, m.list_select_related, m.list_per_page,
                m.list_editable, m)

        cl.get_results(request)

        # There's only one Group instance
        self.assertEqual(cl.result_count, 1)

    def test_distinct_for_through_m2m_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't apper more than once. With an intermediate model.
        """
        lead = Musician.objects.create(name='Vox')
        band = Group.objects.create(name='The Hype')
        Membership.objects.create(group=band, music=lead, role='lead voice')
        Membership.objects.create(group=band, music=lead, role='bass player')

        m = GroupAdmin(Group, admin.site)
        request = MockFilterRequest('members', lead.pk)

        cl = ChangeList(request, Group, m.list_display,
                m.list_display_links, m.list_filter, m.date_hierarchy,
                m.search_fields, m.list_select_related, m.list_per_page,
                m.list_editable, m)

        cl.get_results(request)

        # There's only one Group instance
        self.assertEqual(cl.result_count, 1)

    def test_distinct_for_inherited_m2m_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't apper more than once. Model managed in the
        admin inherits from the one that defins the relationship.
        """
        lead = Musician.objects.create(name='John')
        four = Quartet.objects.create(name='The Beatles')
        Membership.objects.create(group=four, music=lead, role='lead voice')
        Membership.objects.create(group=four, music=lead, role='guitar player')

        m = QuartetAdmin(Quartet, admin.site)
        request = MockFilterRequest('members', lead.pk)

        cl = ChangeList(request, Quartet, m.list_display,
                m.list_display_links, m.list_filter, m.date_hierarchy,
                m.search_fields, m.list_select_related, m.list_per_page,
                m.list_editable, m)

        cl.get_results(request)

        # There's only one Quartet instance
        self.assertEqual(cl.result_count, 1)

    def test_distinct_for_m2m_to_inherited_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't apper more than once. Target of the relationship
        inherits from another.
        """
        lead = ChordsMusician.objects.create(name='Player A')
        three = ChordsBand.objects.create(name='The Chords Trio')
        Invitation.objects.create(band=three, player=lead, instrument='guitar')
        Invitation.objects.create(band=three, player=lead, instrument='bass')

        m = ChordsBandAdmin(ChordsBand, admin.site)
        request = MockFilterRequest('members', lead.pk)

        cl = ChangeList(request, ChordsBand, m.list_display,
                m.list_display_links, m.list_filter, m.date_hierarchy,
                m.search_fields, m.list_select_related, m.list_per_page,
                m.list_editable, m)

        cl.get_results(request)

        # There's only one ChordsBand instance
        self.assertEqual(cl.result_count, 1)

    def test_distinct_for_non_unique_related_object_in_list_filter(self):
        """
        Regressions tests for #15819: If a field listed in list_filters
        is a non-unique related object, distinct() must be called.
        """
        parent = Parent.objects.create(name='Mary')
        # Two children with the same name
        Child.objects.create(parent=parent, name='Daniel')
        Child.objects.create(parent=parent, name='Daniel')

        m = ParentAdmin(Parent, admin.site)
        request = MockFilterRequest('child__name', 'Daniel')

        cl = ChangeList(request, Parent, m.list_display, m.list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_editable, m)

        # Make sure distinct() was called
        self.assertEqual(cl.query_set.count(), 1)

    def test_distinct_for_non_unique_related_object_in_search_fields(self):
        """
        Regressions tests for #15819: If a field listed in search_fields
        is a non-unique related object, distinct() must be called.
        """
        parent = Parent.objects.create(name='Mary')
        Child.objects.create(parent=parent, name='Danielle')
        Child.objects.create(parent=parent, name='Daniel')

        m = ParentAdmin(Parent, admin.site)
        request = MockSearchRequest('daniel')

        cl = ChangeList(request, Parent, m.list_display, m.list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_editable, m)

        # Make sure distinct() was called
        self.assertEqual(cl.query_set.count(), 1)

    def test_pagination(self):
        """
        Regression tests for #12893: Pagination in admins changelist doesn't
        use queryset set by modeladmin.
        """
        parent = Parent.objects.create(name='anything')
        for i in range(30):
            Child.objects.create(name='name %s' % i, parent=parent)
            Child.objects.create(name='filtered %s' % i, parent=parent)

        request = MockRequest()

        # Test default queryset
        m = ChildAdmin(Child, admin.site)
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_editable, m)
        self.assertEqual(cl.query_set.count(), 60)
        self.assertEqual(cl.paginator.count, 60)
        self.assertEqual(cl.paginator.page_range, [1, 2, 3, 4, 5, 6])

        # Test custom queryset
        m = FilteredChildAdmin(Child, admin.site)
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_editable, m)
        self.assertEqual(cl.query_set.count(), 30)
        self.assertEqual(cl.paginator.count, 30)
        self.assertEqual(cl.paginator.page_range, [1, 2, 3])


class ParentAdmin(admin.ModelAdmin):
    list_filter = ['child__name']
    search_fields = ['child__name']


class ChildAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    list_per_page = 10
    def queryset(self, request):
        return super(ChildAdmin, self).queryset(request).select_related("parent__name")

class FilteredChildAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    list_per_page = 10
    def queryset(self, request):
        return super(FilteredChildAdmin, self).queryset(request).filter(
            name__contains='filtered')

class MockRequest(object):
    GET = {}

class CustomPaginator(Paginator):
    def __init__(self, queryset, page_size, orphans=0, allow_empty_first_page=True):
        super(CustomPaginator, self).__init__(queryset, 5, orphans=2,
            allow_empty_first_page=allow_empty_first_page)


class BandAdmin(admin.ModelAdmin):
    list_filter = ['genres']

class GroupAdmin(admin.ModelAdmin):
    list_filter = ['members']

class QuartetAdmin(admin.ModelAdmin):
    list_filter = ['members']

class ChordsBandAdmin(admin.ModelAdmin):
    list_filter = ['members']

class MockFilterRequest(object):
    def __init__(self, filter, q):
        self.GET = {filter: q}

class MockSearchRequest(object):
    def __init__(self, q):
        self.GET = {SEARCH_VAR: q}
