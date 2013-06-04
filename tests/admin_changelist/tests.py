from __future__ import absolute_import, unicode_literals

import datetime

from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.templatetags.admin_list import pagination
from django.contrib.admin.views.main import ChangeList, SEARCH_VAR, ALL_VAR
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template import Context, Template
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import formats
from django.utils import six

from .admin import (ChildAdmin, QuartetAdmin, BandAdmin, ChordsBandAdmin,
    GroupAdmin, ParentAdmin, DynamicListDisplayChildAdmin,
    DynamicListDisplayLinksChildAdmin, CustomPaginationAdmin,
    FilteredChildAdmin, CustomPaginator, site as custom_site,
    SwallowAdmin, DynamicListFilterChildAdmin, InvitationAdmin)
from .models import (Event, Child, Parent, Genre, Band, Musician, Group,
    Quartet, Membership, ChordsMusician, ChordsBand, Invitation, Swallow,
    UnorderedObject, OrderedObject, CustomIdUser)


class ChangeListTests(TestCase):
    urls = "admin_changelist.urls"

    def setUp(self):
        self.factory = RequestFactory()

    def _create_superuser(self, username):
        return User.objects.create(username=username, is_superuser=True)

    def _mocked_authenticated_request(self, url, user):
        request = self.factory.get(url)
        request.user = user
        return request

    def test_select_related_preserved(self):
        """
        Regression test for #10348: ChangeList.get_queryset() shouldn't
        overwrite a custom select_related provided by ModelAdmin.get_queryset().
        """
        m = ChildAdmin(Child, admin.site)
        request = self.factory.get('/child/')
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)
        self.assertEqual(cl.queryset.query.select_related, {
            'parent': {'name': {}}
        })

    def test_select_related_as_tuple(self):
        ia = InvitationAdmin(Invitation, admin.site)
        request = self.factory.get('/invitation/')
        cl = ChangeList(request, Child, ia.list_display, ia.list_display_links,
                        ia.list_filter, ia.date_hierarchy, ia.search_fields,
                        ia.list_select_related, ia.list_per_page,
                        ia.list_max_show_all, ia.list_editable, ia)
        self.assertEqual(cl.queryset.query.select_related, {'player': {}})

    def test_select_related_as_empty_tuple(self):
        ia = InvitationAdmin(Invitation, admin.site)
        ia.list_select_related = ()
        request = self.factory.get('/invitation/')
        cl = ChangeList(request, Child, ia.list_display, ia.list_display_links,
                        ia.list_filter, ia.date_hierarchy, ia.search_fields,
                        ia.list_select_related, ia.list_per_page,
                        ia.list_max_show_all, ia.list_editable, ia)
        self.assertEqual(cl.queryset.query.select_related, False)


    def test_result_list_empty_changelist_value(self):
        """
        Regression test for #14982: EMPTY_CHANGELIST_VALUE should be honored
        for relationship fields
        """
        new_child = Child.objects.create(name='name', parent=None)
        request = self.factory.get('/child/')
        m = ChildAdmin(Child, admin.site)
        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        cl = ChangeList(request, Child, list_display, list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_max_show_all, m.list_editable, m)
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        link = reverse('admin:admin_changelist_child_change', args=(new_child.id,))
        row_html = '<tbody><tr class="row1"><th><a href="%s">name</a></th><td class="nowrap">(None)</td></tr></tbody>' % link
        self.assertFalse(table_output.find(row_html) == -1,
            'Failed to find expected row element: %s' % table_output)

    def test_result_list_html(self):
        """
        Verifies that inclusion tag result_list generates a table when with
        default ModelAdmin settings.
        """
        new_parent = Parent.objects.create(name='parent')
        new_child = Child.objects.create(name='name', parent=new_parent)
        request = self.factory.get('/child/')
        m = ChildAdmin(Child, admin.site)
        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        cl = ChangeList(request, Child, list_display, list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_max_show_all, m.list_editable, m)
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        link = reverse('admin:admin_changelist_child_change', args=(new_child.id,))
        row_html = '<tbody><tr class="row1"><th><a href="%s">name</a></th><td class="nowrap">Parent object</td></tr></tbody>' % link
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
        request = self.factory.get('/child/')
        m = ChildAdmin(Child, admin.site)

        # Test with list_editable fields
        m.list_display = ['id', 'name', 'parent']
        m.list_display_links = ['id']
        m.list_editable = ['name']
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_max_show_all, m.list_editable, m)
        FormSet = m.get_changelist_formset(request)
        cl.formset = FormSet(queryset=cl.result_list)
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        # make sure that hidden fields are in the correct place
        hiddenfields_div = '<div class="hiddenfields"><input type="hidden" name="form-0-id" value="%d" id="id_form-0-id" /></div>' % new_child.id
        self.assertInHTML(hiddenfields_div, table_output, msg_prefix='Failed to find hidden fields')

        # make sure that list editable fields are rendered in divs correctly
        editable_name_field = '<input name="form-0-name" value="name" class="vTextField" maxlength="30" type="text" id="id_form-0-name" />'
        self.assertInHTML('<td>%s</td>' % editable_name_field, table_output, msg_prefix='Failed to find "name" list_editable field')

    def test_result_list_editable(self):
        """
        Regression test for #14312: list_editable with pagination
        """

        new_parent = Parent.objects.create(name='parent')
        for i in range(200):
            new_child = Child.objects.create(name='name %s' % i, parent=new_parent)
        request = self.factory.get('/child/', data={'p': -1})  # Anything outside range
        m = ChildAdmin(Child, admin.site)

        # Test with list_editable fields
        m.list_display = ['id', 'name', 'parent']
        m.list_display_links = ['id']
        m.list_editable = ['name']
        self.assertRaises(IncorrectLookupParameters, lambda: \
            ChangeList(request, Child, m.list_display, m.list_display_links,
                    m.list_filter, m.date_hierarchy, m.search_fields,
                    m.list_select_related, m.list_per_page, m.list_max_show_all, m.list_editable, m))

    def test_custom_paginator(self):
        new_parent = Parent.objects.create(name='parent')
        for i in range(200):
            new_child = Child.objects.create(name='name %s' % i, parent=new_parent)

        request = self.factory.get('/child/')
        m = CustomPaginationAdmin(Child, admin.site)

        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_max_show_all, m.list_editable, m)

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
        request = self.factory.get('/band/', data={'genres': blues.pk})

        cl = ChangeList(request, Band, m.list_display,
                m.list_display_links, m.list_filter, m.date_hierarchy,
                m.search_fields, m.list_select_related, m.list_per_page,
                m.list_max_show_all, m.list_editable, m)

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
        request = self.factory.get('/group/', data={'members': lead.pk})

        cl = ChangeList(request, Group, m.list_display,
                m.list_display_links, m.list_filter, m.date_hierarchy,
                m.search_fields, m.list_select_related, m.list_per_page,
                m.list_max_show_all, m.list_editable, m)

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
        request = self.factory.get('/quartet/', data={'members': lead.pk})

        cl = ChangeList(request, Quartet, m.list_display,
                m.list_display_links, m.list_filter, m.date_hierarchy,
                m.search_fields, m.list_select_related, m.list_per_page,
                m.list_max_show_all, m.list_editable, m)

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
        request = self.factory.get('/chordsband/', data={'members': lead.pk})

        cl = ChangeList(request, ChordsBand, m.list_display,
                m.list_display_links, m.list_filter, m.date_hierarchy,
                m.search_fields, m.list_select_related, m.list_per_page,
                m.list_max_show_all, m.list_editable, m)

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
        request = self.factory.get('/parent/', data={'child__name': 'Daniel'})

        cl = ChangeList(request, Parent, m.list_display, m.list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)

        # Make sure distinct() was called
        self.assertEqual(cl.queryset.count(), 1)

    def test_distinct_for_non_unique_related_object_in_search_fields(self):
        """
        Regressions tests for #15819: If a field listed in search_fields
        is a non-unique related object, distinct() must be called.
        """
        parent = Parent.objects.create(name='Mary')
        Child.objects.create(parent=parent, name='Danielle')
        Child.objects.create(parent=parent, name='Daniel')

        m = ParentAdmin(Parent, admin.site)
        request = self.factory.get('/parent/', data={SEARCH_VAR: 'daniel'})

        cl = ChangeList(request, Parent, m.list_display, m.list_display_links,
                        m.list_filter, m.date_hierarchy, m.search_fields,
                        m.list_select_related, m.list_per_page,
                        m.list_max_show_all, m.list_editable, m)

        # Make sure distinct() was called
        self.assertEqual(cl.queryset.count(), 1)

    def test_pagination(self):
        """
        Regression tests for #12893: Pagination in admins changelist doesn't
        use queryset set by modeladmin.
        """
        parent = Parent.objects.create(name='anything')
        for i in range(30):
            Child.objects.create(name='name %s' % i, parent=parent)
            Child.objects.create(name='filtered %s' % i, parent=parent)

        request = self.factory.get('/child/')

        # Test default queryset
        m = ChildAdmin(Child, admin.site)
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_max_show_all,
                m.list_editable, m)
        self.assertEqual(cl.queryset.count(), 60)
        self.assertEqual(cl.paginator.count, 60)
        self.assertEqual(list(cl.paginator.page_range), [1, 2, 3, 4, 5, 6])

        # Test custom queryset
        m = FilteredChildAdmin(Child, admin.site)
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, m.list_max_show_all,
                m.list_editable, m)
        self.assertEqual(cl.queryset.count(), 30)
        self.assertEqual(cl.paginator.count, 30)
        self.assertEqual(list(cl.paginator.page_range), [1, 2, 3])

    def test_computed_list_display_localization(self):
        """
        Regression test for #13196: output of functions should be  localized
        in the changelist.
        """
        User.objects.create_superuser(
            username='super', email='super@localhost', password='secret')
        self.client.login(username='super', password='secret')
        event = Event.objects.create(date=datetime.date.today())
        response = self.client.get('/admin/admin_changelist/event/')
        self.assertContains(response, formats.localize(event.date))
        self.assertNotContains(response, six.text_type(event.date))

    def test_dynamic_list_display(self):
        """
        Regression tests for #14206: dynamic list_display support.
        """
        parent = Parent.objects.create(name='parent')
        for i in range(10):
            Child.objects.create(name='child %s' % i, parent=parent)

        user_noparents = self._create_superuser('noparents')
        user_parents = self._create_superuser('parents')

        # Test with user 'noparents'
        m = custom_site._registry[Child]
        request = self._mocked_authenticated_request('/child/', user_noparents)
        response = m.changelist_view(request)
        self.assertNotContains(response, 'Parent object')

        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        self.assertEqual(list_display, ['name', 'age'])
        self.assertEqual(list_display_links, ['name'])

        # Test with user 'parents'
        m = DynamicListDisplayChildAdmin(Child, admin.site)
        request = self._mocked_authenticated_request('/child/', user_parents)
        response = m.changelist_view(request)
        self.assertContains(response, 'Parent object')

        custom_site.unregister(Child)

        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        self.assertEqual(list_display, ('parent', 'name', 'age'))
        self.assertEqual(list_display_links, ['parent'])

        # Test default implementation
        custom_site.register(Child, ChildAdmin)
        m = custom_site._registry[Child]
        request = self._mocked_authenticated_request('/child/', user_noparents)
        response = m.changelist_view(request)
        self.assertContains(response, 'Parent object')

    def test_show_all(self):
        parent = Parent.objects.create(name='anything')
        for i in range(30):
            Child.objects.create(name='name %s' % i, parent=parent)
            Child.objects.create(name='filtered %s' % i, parent=parent)

        # Add "show all" parameter to request
        request = self.factory.get('/child/', data={ALL_VAR: ''})

        # Test valid "show all" request (number of total objects is under max)
        m = ChildAdmin(Child, admin.site)
        # 200 is the max we'll pass to ChangeList
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, 200, m.list_editable, m)
        cl.get_results(request)
        self.assertEqual(len(cl.result_list), 60)

        # Test invalid "show all" request (number of total objects over max)
        # falls back to paginated pages
        m = ChildAdmin(Child, admin.site)
        # 30 is the max we'll pass to ChangeList for this test
        cl = ChangeList(request, Child, m.list_display, m.list_display_links,
                m.list_filter, m.date_hierarchy, m.search_fields,
                m.list_select_related, m.list_per_page, 30, m.list_editable, m)
        cl.get_results(request)
        self.assertEqual(len(cl.result_list), 10)

    def test_dynamic_list_display_links(self):
        """
        Regression tests for #16257: dynamic list_display_links support.
        """
        parent = Parent.objects.create(name='parent')
        for i in range(1, 10):
            Child.objects.create(id=i, name='child %s' % i, parent=parent, age=i)

        m = DynamicListDisplayLinksChildAdmin(Child, admin.site)
        superuser = self._create_superuser('superuser')
        request = self._mocked_authenticated_request('/child/', superuser)
        response = m.changelist_view(request)
        for i in range(1, 10):
            link = reverse('admin:admin_changelist_child_change', args=(i,))
            self.assertContains(response, '<a href="%s">%s</a>' % (link, i))

        list_display = m.get_list_display(request)
        list_display_links = m.get_list_display_links(request, list_display)
        self.assertEqual(list_display, ('parent', 'name', 'age'))
        self.assertEqual(list_display_links, ['age'])

    def test_tuple_list_display(self):
        """
        Regression test for #17128
        (ChangeList failing under Python 2.5 after r16319)
        """
        swallow = Swallow.objects.create(
            origin='Africa', load='12.34', speed='22.2')
        model_admin = SwallowAdmin(Swallow, admin.site)
        superuser = self._create_superuser('superuser')
        request = self._mocked_authenticated_request('/swallow/', superuser)
        response = model_admin.changelist_view(request)
        # just want to ensure it doesn't blow up during rendering
        self.assertContains(response, six.text_type(swallow.origin))
        self.assertContains(response, six.text_type(swallow.load))
        self.assertContains(response, six.text_type(swallow.speed))

    def test_deterministic_order_for_unordered_model(self):
        """
        Ensure that the primary key is systematically used in the ordering of
        the changelist's results to guarantee a deterministic order, even
        when the Model doesn't have any default ordering defined.
        Refs #17198.
        """
        superuser = self._create_superuser('superuser')

        for counter in range(1, 51):
            UnorderedObject.objects.create(id=counter, bool=True)

        class UnorderedObjectAdmin(admin.ModelAdmin):
            list_per_page = 10

        def check_results_order(ascending=False):
            admin.site.register(UnorderedObject, UnorderedObjectAdmin)
            model_admin = UnorderedObjectAdmin(UnorderedObject, admin.site)
            counter = 0 if ascending else 51
            for page in range (0, 5):
                request = self._mocked_authenticated_request('/unorderedobject/?p=%s' % page, superuser)
                response = model_admin.changelist_view(request)
                for result in response.context_data['cl'].result_list:
                    counter += 1 if ascending else -1
                    self.assertEqual(result.id, counter)
            admin.site.unregister(UnorderedObject)

        # When no order is defined at all, everything is ordered by '-pk'.
        check_results_order()

        # When an order field is defined but multiple records have the same
        # value for that field, make sure everything gets ordered by -pk as well.
        UnorderedObjectAdmin.ordering = ['bool']
        check_results_order()

        # When order fields are defined, including the pk itself, use them.
        UnorderedObjectAdmin.ordering = ['bool', '-pk']
        check_results_order()
        UnorderedObjectAdmin.ordering = ['bool', 'pk']
        check_results_order(ascending=True)
        UnorderedObjectAdmin.ordering = ['-id', 'bool']
        check_results_order()
        UnorderedObjectAdmin.ordering = ['id', 'bool']
        check_results_order(ascending=True)

    def test_deterministic_order_for_model_ordered_by_its_manager(self):
        """
        Ensure that the primary key is systematically used in the ordering of
        the changelist's results to guarantee a deterministic order, even
        when the Model has a manager that defines a default ordering.
        Refs #17198.
        """
        superuser = self._create_superuser('superuser')

        for counter in range(1, 51):
            OrderedObject.objects.create(id=counter, bool=True, number=counter)

        class OrderedObjectAdmin(admin.ModelAdmin):
            list_per_page = 10

        def check_results_order(ascending=False):
            admin.site.register(OrderedObject, OrderedObjectAdmin)
            model_admin = OrderedObjectAdmin(OrderedObject, admin.site)
            counter = 0 if ascending else 51
            for page in range (0, 5):
                request = self._mocked_authenticated_request('/orderedobject/?p=%s' % page, superuser)
                response = model_admin.changelist_view(request)
                for result in response.context_data['cl'].result_list:
                    counter += 1 if ascending else -1
                    self.assertEqual(result.id, counter)
            admin.site.unregister(OrderedObject)

        # When no order is defined at all, use the model's default ordering (i.e. 'number')
        check_results_order(ascending=True)

        # When an order field is defined but multiple records have the same
        # value for that field, make sure everything gets ordered by -pk as well.
        OrderedObjectAdmin.ordering = ['bool']
        check_results_order()

        # When order fields are defined, including the pk itself, use them.
        OrderedObjectAdmin.ordering = ['bool', '-pk']
        check_results_order()
        OrderedObjectAdmin.ordering = ['bool', 'pk']
        check_results_order(ascending=True)
        OrderedObjectAdmin.ordering = ['-id', 'bool']
        check_results_order()
        OrderedObjectAdmin.ordering = ['id', 'bool']
        check_results_order(ascending=True)

    def test_dynamic_list_filter(self):
        """
        Regression tests for ticket #17646: dynamic list_filter support.
        """
        parent = Parent.objects.create(name='parent')
        for i in range(10):
            Child.objects.create(name='child %s' % i, parent=parent)

        user_noparents = self._create_superuser('noparents')
        user_parents = self._create_superuser('parents')

        # Test with user 'noparents'
        m =  DynamicListFilterChildAdmin(Child, admin.site)
        request = self._mocked_authenticated_request('/child/', user_noparents)
        response = m.changelist_view(request)
        self.assertEqual(response.context_data['cl'].list_filter, ['name', 'age'])

        # Test with user 'parents'
        m = DynamicListFilterChildAdmin(Child, admin.site)
        request = self._mocked_authenticated_request('/child/', user_parents)
        response = m.changelist_view(request)
        self.assertEqual(response.context_data['cl'].list_filter, ('parent', 'name', 'age'))

    def test_pagination_page_range(self):
        """
        Regression tests for ticket #15653: ensure the number of pages
        generated for changelist views are correct.
        """
        # instantiating and setting up ChangeList object
        m = GroupAdmin(Group, admin.site)
        request = self.factory.get('/group/')
        cl = ChangeList(request, Group, m.list_display,
                m.list_display_links, m.list_filter, m.date_hierarchy,
                m.search_fields, m.list_select_related, m.list_per_page,
                m.list_max_show_all, m.list_editable, m)
        per_page = cl.list_per_page = 10

        for page_num, objects_count, expected_page_range in [
            (0, per_page, []),
            (0, per_page * 2, list(range(2))),
            (5, per_page * 11, list(range(11))),
            (5, per_page * 12, [0, 1, 2, 3, 4, 5, 6, 7, 8, '.', 10, 11]),
            (6, per_page * 12, [0, 1, '.', 3, 4, 5, 6, 7, 8, 9, 10, 11]),
            (6, per_page * 13, [0, 1, '.', 3, 4, 5, 6, 7, 8, 9, '.', 11, 12]),
        ]:
            # assuming we have exactly `objects_count` objects
            Group.objects.all().delete()
            for i in range(objects_count):
                Group.objects.create(name='test band')

            # setting page number and calculating page range
            cl.page_num = page_num
            cl.get_results(request)
            real_page_range = pagination(cl)['page_range']

            self.assertListEqual(
                expected_page_range,
                list(real_page_range),
            )


class AdminLogNodeTestCase(TestCase):

    def test_get_admin_log_templatetag_custom_user(self):
        """
        Regression test for ticket #20088: admin log depends on User model
        having id field as primary key.

        The old implementation raised an AttributeError when trying to use
        the id field.
        """
        context = Context({'user': CustomIdUser()})
        template_string = '{% load log %}{% get_admin_log 10 as admin_log for_user user %}'

        template = Template(template_string)

        # Rendering should be u'' since this templatetag just logs,
        # it doesn't render any string.
        self.assertEqual(template.render(context), '')
