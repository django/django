from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.template import Context, Template
from django.test import TransactionTestCase
from regressiontests.admin_changelist.models import Child, Parent

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
        row_html = '<tbody><tr class="row1"><td><input type="checkbox" class="action-select" value="1" name="_selected_action" /></td><th><a href="1/">name</a></th><td>Parent object</td></tr></tbody>'
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
        hiddenfields_div = '<div class="hiddenfields"><input type="hidden" name="form-0-id" value="1" id="id_form-0-id" /></div>'
        self.assertFalse(table_output.find(hiddenfields_div) == -1,
            'Failed to find hidden fields in: %s' % table_output)
        # make sure that list editable fields are rendered in divs correctly
        editable_name_field = '<input name="form-0-name" value="name" class="vTextField" maxlength="30" type="text" id="id_form-0-name" />'
        self.assertFalse('<td>%s</td>' % editable_name_field == -1,
            'Failed to find "name" list_editable field in: %s' % table_output)

class ChildAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    def queryset(self, request):
        return super(ChildAdmin, self).queryset(request).select_related("parent__name")

class MockRequest(object):
    GET = {}
