import datetime

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.templatetags.admin_list import pagination
from django.contrib.admin.tests import AdminSeleniumTestCase
from django.contrib.admin.views.main import ALL_VAR, SEARCH_VAR, ChangeList
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils import formats

from .admin import (
    BandAdmin, ChildAdmin, ChordsBandAdmin, ConcertAdmin,
    CustomPaginationAdmin, CustomPaginator, DynamicListDisplayChildAdmin,
    DynamicListDisplayLinksChildAdmin, DynamicListFilterChildAdmin,
    DynamicSearchFieldsChildAdmin, EmptyValueChildAdmin, EventAdmin,
    FilteredChildAdmin, GroupAdmin, InvitationAdmin,
    NoListDisplayLinksParentAdmin, ParentAdmin, QuartetAdmin, SwallowAdmin,
    site as custom_site,
)
from .models import (
    Band, Child, ChordsBand, ChordsMusician, Concert, CustomIdUser, Event,
    Genre, Group, Invitation, Membership, Musician, OrderedObject, Parent,
    Quartet, Swallow, SwallowOneToOne, UnorderedObject,
)


def get_changelist_args(modeladmin, **kwargs):
    m = modeladmin
    args = (
        kwargs.pop('list_display', m.list_display),
        kwargs.pop('list_display_links', m.list_display_links),
        kwargs.pop('list_filter', m.list_filter),
        kwargs.pop('date_hierarchy', m.date_hierarchy),
        kwargs.pop('search_fields', m.search_fields),
        kwargs.pop('list_select_related', m.list_select_related),
        kwargs.pop('list_per_page', m.list_per_page),
        kwargs.pop('list_max_show_all', m.list_max_show_all),
        kwargs.pop('list_editable', m.list_editable),
        m,
    )
    assert not kwargs, "Unexpected kwarg %s" % kwargs
    return args


@override_settings(ROOT_URLCONF="admin_changelist.urls")
class ChangeListTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _create_superuser(self, username):
        return User.objects.create_superuser(username=username, email='a@b.com', password='xxx')

    def _mocked_authenticated_request(self, url, user):
        request = self.factory.get(url)
        request.user = user
        return request

    def test_select_related_preserved(self):
        """
        Regression test for #10348: ChangeList.get_queryset() shouldn't
        overwrite a custom select_related provided by ModelAdmin.get_queryset().
        """
        m = ChildAdmin(Child, custom_site)
        request = self.factory.get('/child/')
        cl = ChangeList(
            request, Child,
            *get_changelist_args(m, list_select_related=m.get_list_select_related(request))
        )
        self.assertEqual(cl.queryset.query.select_related, {'parent': {}})

    def test_select_related_as_tuple(self):
        ia = InvitationAdmin(Invitation, custom_site)
        request = self.factory.get('/invitation/')
        cl = ChangeList(
            request, Child,
            *get_changelist_args(ia, list_select_related=ia.get_list_select_related(request))
        )
        self.assertEqual(cl.queryset.query.select_related, {'player': {}})

    def test_select_related_as_empty_tuple(self):
        ia = InvitationAdmin(Invitation, custom_site)
        ia.list_select_related = ()
        request = self.factory.get('/invitation/')
        cl = ChangeList(
            request, Child,
            *get_changelist_args(ia, list_select_related=ia.get_list_select_related(request))
        )
        self.assertIs(cl.queryset.query.select_related, False)

    def test_get_select_related_custom_method(self):
        class GetListSelectRelatedAdmin(admin.ModelAdmin):
            list_display = ('band', 'player')

            def get_list_select_related(self, request):
                return ('band', 'player')

        ia = GetListSelectRelatedAdmin(Invitation, custom_site)
        request = self.factory.get('/invitation/')
        cl = ChangeList(
            request, Child,
            *get_changelist_args(ia, list_select_related=ia.get_list_select_related(request))
        )
        self.assertEqual(cl.queryset.query.select_related, {'player': {}, 'band': {}})

    def test_result_list_empty_changelist_value(self):
        """
        Regression test for #14982: EMPTY_CHANGELIST_VALUE should be honored
        for relationship fields
        """
        new_child = Child.objects.create(name='name', parent=None)
        request = self.factory.get('/child/')
        m = ChildAdmin(Child, custom_site)
        cl = ChangeList(request, Child, *get_changelist_args(m))
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        link = reverse('admin:admin_changelist_child_change', args=(new_child.id,))
        row_html = (
            '<tbody><tr class="row1"><th class="field-name"><a href="%s">name</a></th>'
            '<td class="field-parent nowrap">-</td></tr></tbody>' % link
        )
        self.assertNotEqual(table_output.find(row_html), -1, 'Failed to find expected row element: %s' % table_output)

    def test_result_list_set_empty_value_display_on_admin_site(self):
        """
        Empty value display can be set on AdminSite.
        """
        new_child = Child.objects.create(name='name', parent=None)
        request = self.factory.get('/child/')
        # Set a new empty display value on AdminSite.
        admin.site.empty_value_display = '???'
        m = ChildAdmin(Child, admin.site)
        cl = ChangeList(request, Child, *get_changelist_args(m))
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        link = reverse('admin:admin_changelist_child_change', args=(new_child.id,))
        row_html = (
            '<tbody><tr class="row1"><th class="field-name"><a href="%s">name</a></th>'
            '<td class="field-parent nowrap">???</td></tr></tbody>' % link
        )
        self.assertNotEqual(table_output.find(row_html), -1, 'Failed to find expected row element: %s' % table_output)

    def test_result_list_set_empty_value_display_in_model_admin(self):
        """
        Empty value display can be set in ModelAdmin or individual fields.
        """
        new_child = Child.objects.create(name='name', parent=None)
        request = self.factory.get('/child/')
        m = EmptyValueChildAdmin(Child, admin.site)
        cl = ChangeList(request, Child, *get_changelist_args(m))
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        link = reverse('admin:admin_changelist_child_change', args=(new_child.id,))
        row_html = (
            '<tbody><tr class="row1"><th class="field-name"><a href="%s">name</a></th>'
            '<td class="field-age_display">&amp;dagger;</td><td class="field-age">-empty-</td></tr></tbody>' % link
        )
        self.assertNotEqual(table_output.find(row_html), -1, 'Failed to find expected row element: %s' % table_output)

    def test_result_list_html(self):
        """
        Inclusion tag result_list generates a table when with default
        ModelAdmin settings.
        """
        new_parent = Parent.objects.create(name='parent')
        new_child = Child.objects.create(name='name', parent=new_parent)
        request = self.factory.get('/child/')
        m = ChildAdmin(Child, custom_site)
        cl = ChangeList(request, Child, *get_changelist_args(m))
        cl.formset = None
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        link = reverse('admin:admin_changelist_child_change', args=(new_child.id,))
        row_html = (
            '<tbody><tr class="row1"><th class="field-name"><a href="%s">name</a></th>'
            '<td class="field-parent nowrap">Parent object</td></tr></tbody>' % link
        )
        self.assertNotEqual(table_output.find(row_html), -1, 'Failed to find expected row element: %s' % table_output)

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
        m = ChildAdmin(Child, custom_site)

        # Test with list_editable fields
        m.list_display = ['id', 'name', 'parent']
        m.list_display_links = ['id']
        m.list_editable = ['name']
        cl = ChangeList(request, Child, *get_changelist_args(m))
        FormSet = m.get_changelist_formset(request)
        cl.formset = FormSet(queryset=cl.result_list)
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        # make sure that hidden fields are in the correct place
        hiddenfields_div = (
            '<div class="hiddenfields">'
            '<input type="hidden" name="form-0-id" value="%d" id="id_form-0-id" />'
            '</div>'
        ) % new_child.id
        self.assertInHTML(hiddenfields_div, table_output, msg_prefix='Failed to find hidden fields')

        # make sure that list editable fields are rendered in divs correctly
        editable_name_field = (
            '<input name="form-0-name" value="name" class="vTextField" '
            'maxlength="30" type="text" id="id_form-0-name" />'
        )
        self.assertInHTML(
            '<td class="field-name">%s</td>' % editable_name_field,
            table_output,
            msg_prefix='Failed to find "name" list_editable field',
        )

    def test_result_list_editable(self):
        """
        Regression test for #14312: list_editable with pagination
        """
        new_parent = Parent.objects.create(name='parent')
        for i in range(200):
            Child.objects.create(name='name %s' % i, parent=new_parent)
        request = self.factory.get('/child/', data={'p': -1})  # Anything outside range
        m = ChildAdmin(Child, custom_site)

        # Test with list_editable fields
        m.list_display = ['id', 'name', 'parent']
        m.list_display_links = ['id']
        m.list_editable = ['name']
        with self.assertRaises(IncorrectLookupParameters):
            ChangeList(request, Child, *get_changelist_args(m))

    def test_custom_paginator(self):
        new_parent = Parent.objects.create(name='parent')
        for i in range(200):
            Child.objects.create(name='name %s' % i, parent=new_parent)

        request = self.factory.get('/child/')
        m = CustomPaginationAdmin(Child, custom_site)

        cl = ChangeList(request, Child, *get_changelist_args(m))
        cl.get_results(request)
        self.assertIsInstance(cl.paginator, CustomPaginator)

    def test_distinct_for_m2m_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't appear more than once. Basic ManyToMany.
        """
        blues = Genre.objects.create(name='Blues')
        band = Band.objects.create(name='B.B. King Review', nr_of_members=11)

        band.genres.add(blues)
        band.genres.add(blues)

        m = BandAdmin(Band, custom_site)
        request = self.factory.get('/band/', data={'genres': blues.pk})

        cl = ChangeList(request, Band, *get_changelist_args(m))
        cl.get_results(request)

        # There's only one Group instance
        self.assertEqual(cl.result_count, 1)

    def test_distinct_for_through_m2m_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't appear more than once. With an intermediate model.
        """
        lead = Musician.objects.create(name='Vox')
        band = Group.objects.create(name='The Hype')
        Membership.objects.create(group=band, music=lead, role='lead voice')
        Membership.objects.create(group=band, music=lead, role='bass player')

        m = GroupAdmin(Group, custom_site)
        request = self.factory.get('/group/', data={'members': lead.pk})

        cl = ChangeList(request, Group, *get_changelist_args(m))
        cl.get_results(request)

        # There's only one Group instance
        self.assertEqual(cl.result_count, 1)

    def test_distinct_for_through_m2m_at_second_level_in_list_filter(self):
        """
        When using a ManyToMany in list_filter at the second level behind a
        ForeignKey, distinct() must be called and results shouldn't appear more
        than once.
        """
        lead = Musician.objects.create(name='Vox')
        band = Group.objects.create(name='The Hype')
        Concert.objects.create(name='Woodstock', group=band)
        Membership.objects.create(group=band, music=lead, role='lead voice')
        Membership.objects.create(group=band, music=lead, role='bass player')

        m = ConcertAdmin(Concert, custom_site)
        request = self.factory.get('/concert/', data={'group__members': lead.pk})

        cl = ChangeList(request, Concert, *get_changelist_args(m))
        cl.get_results(request)

        # There's only one Concert instance
        self.assertEqual(cl.result_count, 1)

    def test_distinct_for_inherited_m2m_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't appear more than once. Model managed in the
        admin inherits from the one that defins the relationship.
        """
        lead = Musician.objects.create(name='John')
        four = Quartet.objects.create(name='The Beatles')
        Membership.objects.create(group=four, music=lead, role='lead voice')
        Membership.objects.create(group=four, music=lead, role='guitar player')

        m = QuartetAdmin(Quartet, custom_site)
        request = self.factory.get('/quartet/', data={'members': lead.pk})

        cl = ChangeList(request, Quartet, *get_changelist_args(m))
        cl.get_results(request)

        # There's only one Quartet instance
        self.assertEqual(cl.result_count, 1)

    def test_distinct_for_m2m_to_inherited_in_list_filter(self):
        """
        Regression test for #13902: When using a ManyToMany in list_filter,
        results shouldn't appear more than once. Target of the relationship
        inherits from another.
        """
        lead = ChordsMusician.objects.create(name='Player A')
        three = ChordsBand.objects.create(name='The Chords Trio')
        Invitation.objects.create(band=three, player=lead, instrument='guitar')
        Invitation.objects.create(band=three, player=lead, instrument='bass')

        m = ChordsBandAdmin(ChordsBand, custom_site)
        request = self.factory.get('/chordsband/', data={'members': lead.pk})

        cl = ChangeList(request, ChordsBand, *get_changelist_args(m))
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

        m = ParentAdmin(Parent, custom_site)
        request = self.factory.get('/parent/', data={'child__name': 'Daniel'})

        cl = ChangeList(request, Parent, *get_changelist_args(m))
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

        m = ParentAdmin(Parent, custom_site)
        request = self.factory.get('/parent/', data={SEARCH_VAR: 'daniel'})

        cl = ChangeList(request, Parent, *get_changelist_args(m))
        # Make sure distinct() was called
        self.assertEqual(cl.queryset.count(), 1)

    def test_distinct_for_many_to_many_at_second_level_in_search_fields(self):
        """
        When using a ManyToMany in search_fields at the second level behind a
        ForeignKey, distinct() must be called and results shouldn't appear more
        than once.
        """
        lead = Musician.objects.create(name='Vox')
        band = Group.objects.create(name='The Hype')
        Concert.objects.create(name='Woodstock', group=band)
        Membership.objects.create(group=band, music=lead, role='lead voice')
        Membership.objects.create(group=band, music=lead, role='bass player')

        m = ConcertAdmin(Concert, custom_site)
        request = self.factory.get('/concert/', data={SEARCH_VAR: 'vox'})

        cl = ChangeList(request, Concert, *get_changelist_args(m))
        # There's only one Concert instance
        self.assertEqual(cl.queryset.count(), 1)

    def test_no_distinct_for_m2m_in_list_filter_without_params(self):
        """
        If a ManyToManyField is in list_filter but isn't in any lookup params,
        the changelist's query shouldn't have distinct.
        """
        m = BandAdmin(Band, custom_site)
        for lookup_params in ({}, {'name': 'test'}):
            request = self.factory.get('/band/', lookup_params)
            cl = ChangeList(request, Band, *get_changelist_args(m))
            self.assertFalse(cl.queryset.query.distinct)

        # A ManyToManyField in params does have distinct applied.
        request = self.factory.get('/band/', {'genres': '0'})
        cl = ChangeList(request, Band, *get_changelist_args(m))
        self.assertTrue(cl.queryset.query.distinct)

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
        m = ChildAdmin(Child, custom_site)
        cl = ChangeList(request, Child, *get_changelist_args(m))
        self.assertEqual(cl.queryset.count(), 60)
        self.assertEqual(cl.paginator.count, 60)
        self.assertEqual(list(cl.paginator.page_range), [1, 2, 3, 4, 5, 6])

        # Test custom queryset
        m = FilteredChildAdmin(Child, custom_site)
        cl = ChangeList(request, Child, *get_changelist_args(m))
        self.assertEqual(cl.queryset.count(), 30)
        self.assertEqual(cl.paginator.count, 30)
        self.assertEqual(list(cl.paginator.page_range), [1, 2, 3])

    def test_computed_list_display_localization(self):
        """
        Regression test for #13196: output of functions should be  localized
        in the changelist.
        """
        superuser = User.objects.create_superuser(username='super', email='super@localhost', password='secret')
        self.client.force_login(superuser)
        event = Event.objects.create(date=datetime.date.today())
        response = self.client.get(reverse('admin:admin_changelist_event_changelist'))
        self.assertContains(response, formats.localize(event.date))
        self.assertNotContains(response, str(event.date))

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
        m = DynamicListDisplayChildAdmin(Child, custom_site)
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
        m = ChildAdmin(Child, custom_site)
        m.list_max_show_all = 200
        # 200 is the max we'll pass to ChangeList
        cl = ChangeList(request, Child, *get_changelist_args(m))
        cl.get_results(request)
        self.assertEqual(len(cl.result_list), 60)

        # Test invalid "show all" request (number of total objects over max)
        # falls back to paginated pages
        m = ChildAdmin(Child, custom_site)
        m.list_max_show_all = 30
        # 30 is the max we'll pass to ChangeList for this test
        cl = ChangeList(request, Child, *get_changelist_args(m))
        cl.get_results(request)
        self.assertEqual(len(cl.result_list), 10)

    def test_dynamic_list_display_links(self):
        """
        Regression tests for #16257: dynamic list_display_links support.
        """
        parent = Parent.objects.create(name='parent')
        for i in range(1, 10):
            Child.objects.create(id=i, name='child %s' % i, parent=parent, age=i)

        m = DynamicListDisplayLinksChildAdmin(Child, custom_site)
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

    def test_no_list_display_links(self):
        """#15185 -- Allow no links from the 'change list' view grid."""
        p = Parent.objects.create(name='parent')
        m = NoListDisplayLinksParentAdmin(Parent, custom_site)
        superuser = self._create_superuser('superuser')
        request = self._mocked_authenticated_request('/parent/', superuser)
        response = m.changelist_view(request)
        link = reverse('admin:admin_changelist_parent_change', args=(p.pk,))
        self.assertNotContains(response, '<a href="%s">' % link)

    def test_tuple_list_display(self):
        """
        Regression test for #17128
        (ChangeList failing under Python 2.5 after r16319)
        """
        swallow = Swallow.objects.create(origin='Africa', load='12.34', speed='22.2')
        swallow2 = Swallow.objects.create(origin='Africa', load='12.34', speed='22.2')
        swallow_o2o = SwallowOneToOne.objects.create(swallow=swallow2)

        model_admin = SwallowAdmin(Swallow, custom_site)
        superuser = self._create_superuser('superuser')
        request = self._mocked_authenticated_request('/swallow/', superuser)
        response = model_admin.changelist_view(request)
        # just want to ensure it doesn't blow up during rendering
        self.assertContains(response, str(swallow.origin))
        self.assertContains(response, str(swallow.load))
        self.assertContains(response, str(swallow.speed))
        # Reverse one-to-one relations should work.
        self.assertContains(response, '<td class="field-swallowonetoone">-</td>')
        self.assertContains(response, '<td class="field-swallowonetoone">%s</td>' % swallow_o2o)

    def test_multiuser_edit(self):
        """
        Simultaneous edits of list_editable fields on the changelist by
        different users must not result in one user's edits creating a new
        object instead of modifying the correct existing object (#11313).
        """
        # To replicate this issue, simulate the following steps:
        # 1. User1 opens an admin changelist with list_editable fields.
        # 2. User2 edits object "Foo" such that it moves to another page in
        #    the pagination order and saves.
        # 3. User1 edits object "Foo" and saves.
        # 4. The edit made by User1 does not get applied to object "Foo" but
        #    instead is used to create a new object (bug).

        # For this test, order the changelist by the 'speed' attribute and
        # display 3 objects per page (SwallowAdmin.list_per_page = 3).

        # Setup the test to reflect the DB state after step 2 where User2 has
        # edited the first swallow object's speed from '4' to '1'.
        a = Swallow.objects.create(origin='Swallow A', load=4, speed=1)
        b = Swallow.objects.create(origin='Swallow B', load=2, speed=2)
        c = Swallow.objects.create(origin='Swallow C', load=5, speed=5)
        d = Swallow.objects.create(origin='Swallow D', load=9, speed=9)

        superuser = self._create_superuser('superuser')
        self.client.force_login(superuser)
        changelist_url = reverse('admin:admin_changelist_swallow_changelist')

        # Send the POST from User1 for step 3. It's still using the changelist
        # ordering from before User2's edits in step 2.
        data = {
            'form-TOTAL_FORMS': '3',
            'form-INITIAL_FORMS': '3',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-id': str(d.pk),
            'form-1-id': str(c.pk),
            'form-2-id': str(a.pk),
            'form-0-load': '9.0',
            'form-0-speed': '9.0',
            'form-1-load': '5.0',
            'form-1-speed': '5.0',
            'form-2-load': '5.0',
            'form-2-speed': '4.0',
            '_save': 'Save',
        }
        response = self.client.post(changelist_url, data, follow=True, extra={'o': '-2'})

        # The object User1 edited in step 3 is displayed on the changelist and
        # has the correct edits applied.
        self.assertContains(response, '1 swallow was changed successfully.')
        self.assertContains(response, a.origin)
        a.refresh_from_db()
        self.assertEqual(a.load, float(data['form-2-load']))
        self.assertEqual(a.speed, float(data['form-2-speed']))
        b.refresh_from_db()
        self.assertEqual(b.load, 2)
        self.assertEqual(b.speed, 2)
        c.refresh_from_db()
        self.assertEqual(c.load, float(data['form-1-load']))
        self.assertEqual(c.speed, float(data['form-1-speed']))
        d.refresh_from_db()
        self.assertEqual(d.load, float(data['form-0-load']))
        self.assertEqual(d.speed, float(data['form-0-speed']))
        # No new swallows were created.
        self.assertEqual(len(Swallow.objects.all()), 4)

    def test_deterministic_order_for_unordered_model(self):
        """
        The primary key is used in the ordering of the changelist's results to
        guarantee a deterministic order, even when the model doesn't have any
        default ordering defined (#17198).
        """
        superuser = self._create_superuser('superuser')

        for counter in range(1, 51):
            UnorderedObject.objects.create(id=counter, bool=True)

        class UnorderedObjectAdmin(admin.ModelAdmin):
            list_per_page = 10

        def check_results_order(ascending=False):
            custom_site.register(UnorderedObject, UnorderedObjectAdmin)
            model_admin = UnorderedObjectAdmin(UnorderedObject, custom_site)
            counter = 0 if ascending else 51
            for page in range(0, 5):
                request = self._mocked_authenticated_request('/unorderedobject/?p=%s' % page, superuser)
                response = model_admin.changelist_view(request)
                for result in response.context_data['cl'].result_list:
                    counter += 1 if ascending else -1
                    self.assertEqual(result.id, counter)
            custom_site.unregister(UnorderedObject)

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
        The primary key is used in the ordering of the changelist's results to
        guarantee a deterministic order, even when the model has a manager that
        defines a default ordering (#17198).
        """
        superuser = self._create_superuser('superuser')

        for counter in range(1, 51):
            OrderedObject.objects.create(id=counter, bool=True, number=counter)

        class OrderedObjectAdmin(admin.ModelAdmin):
            list_per_page = 10

        def check_results_order(ascending=False):
            custom_site.register(OrderedObject, OrderedObjectAdmin)
            model_admin = OrderedObjectAdmin(OrderedObject, custom_site)
            counter = 0 if ascending else 51
            for page in range(0, 5):
                request = self._mocked_authenticated_request('/orderedobject/?p=%s' % page, superuser)
                response = model_admin.changelist_view(request)
                for result in response.context_data['cl'].result_list:
                    counter += 1 if ascending else -1
                    self.assertEqual(result.id, counter)
            custom_site.unregister(OrderedObject)

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
        m = DynamicListFilterChildAdmin(Child, custom_site)
        request = self._mocked_authenticated_request('/child/', user_noparents)
        response = m.changelist_view(request)
        self.assertEqual(response.context_data['cl'].list_filter, ['name', 'age'])

        # Test with user 'parents'
        m = DynamicListFilterChildAdmin(Child, custom_site)
        request = self._mocked_authenticated_request('/child/', user_parents)
        response = m.changelist_view(request)
        self.assertEqual(response.context_data['cl'].list_filter, ('parent', 'name', 'age'))

    def test_dynamic_search_fields(self):
        child = self._create_superuser('child')
        m = DynamicSearchFieldsChildAdmin(Child, custom_site)
        request = self._mocked_authenticated_request('/child/', child)
        response = m.changelist_view(request)
        self.assertEqual(response.context_data['cl'].search_fields, ('name', 'age'))

    def test_pagination_page_range(self):
        """
        Regression tests for ticket #15653: ensure the number of pages
        generated for changelist views are correct.
        """
        # instantiating and setting up ChangeList object
        m = GroupAdmin(Group, custom_site)
        request = self.factory.get('/group/')
        cl = ChangeList(request, Group, *get_changelist_args(m))
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

    def test_object_tools_displayed_no_add_permission(self):
        """
        When ModelAdmin.has_add_permission() returns False, the object-tools
        block is still shown.
        """
        superuser = self._create_superuser('superuser')
        m = EventAdmin(Event, custom_site)
        request = self._mocked_authenticated_request('/event/', superuser)
        self.assertFalse(m.has_add_permission(request))
        response = m.changelist_view(request)
        self.assertIn('<ul class="object-tools">', response.rendered_content)
        # The "Add" button inside the object-tools shouldn't appear.
        self.assertNotIn('Add ', response.rendered_content)


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

    def test_get_admin_log_templatetag_no_user(self):
        """
        The {% get_admin_log %} tag should work without specifying a user.
        """
        user = User(username='jondoe', password='secret', email='super@example.com')
        user.save()
        ct = ContentType.objects.get_for_model(User)
        LogEntry.objects.log_action(user.pk, ct.pk, user.pk, repr(user), 1)

        t = Template(
            '{% load log %}'
            '{% get_admin_log 100 as admin_log %}'
            '{% for entry in admin_log %}'
            '{{ entry|safe }}'
            '{% endfor %}'
        )
        self.assertEqual(t.render(Context({})), 'Added "<User: jondoe>".')


@override_settings(ROOT_URLCONF='admin_changelist.urls')
class SeleniumTests(AdminSeleniumTestCase):

    available_apps = ['admin_changelist'] + AdminSeleniumTestCase.available_apps

    def setUp(self):
        User.objects.create_superuser(username='super', password='secret', email=None)

    def test_add_row_selection(self):
        """
        The status line for selected rows gets updated correctly (#22038).
        """
        self.admin_login(username='super', password='secret')
        self.selenium.get(self.live_server_url + reverse('admin:auth_user_changelist'))

        form_id = '#changelist-form'

        # Test amount of rows in the Changelist
        rows = self.selenium.find_elements_by_css_selector(
            '%s #result_list tbody tr' % form_id)
        self.assertEqual(len(rows), 1)

        # Test current selection
        selection_indicator = self.selenium.find_element_by_css_selector(
            '%s .action-counter' % form_id)
        self.assertEqual(selection_indicator.text, "0 of 1 selected")

        # Select a row and check again
        row_selector = self.selenium.find_element_by_css_selector(
            '%s #result_list tbody tr:first-child .action-select' % form_id)
        row_selector.click()
        self.assertEqual(selection_indicator.text, "1 of 1 selected")
