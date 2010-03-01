import unittest 
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.template import Context, Template
from regressiontests.admin_changelist.models import Child, Parent

class ChangeListTests(unittest.TestCase):
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
        Regression test for #11791: Inclusion tag result_list generates a 
        table and this checks that the items are nested within the table
        element tags.
        """
        new_parent = Parent.objects.create(name='parent')
        new_child = Child.objects.create(name='name', parent=new_parent)
        request = MockRequest()
        m = ChildAdmin(Child, admin.site)
        cl = ChangeList(request, Child, m.list_display, m.list_display_links, 
                m.list_filter, m.date_hierarchy, m.search_fields, 
                m.list_select_related, m.list_per_page, m.list_editable, m)
        FormSet = m.get_changelist_formset(request)
        cl.formset = FormSet(queryset=cl.result_list)
        template = Template('{% load admin_list %}{% spaceless %}{% result_list cl %}{% endspaceless %}')
        context = Context({'cl': cl})
        table_output = template.render(context)
        hidden_input_elem = '<input type="hidden" name="form-0-id" value="1" id="id_form-0-id" />' 
        self.failIf(table_output.find(hidden_input_elem) == -1,
            'Failed to find expected hidden input element in: %s' % table_output)
        self.failIf(table_output.find('<td>%s</td>' % hidden_input_elem) == -1,
            'Hidden input element is not enclosed in <td> element.')

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
        self.failIf(table_output.find(hidden_input_elem) == -1,
            'Failed to find expected hidden input element in: %s' % table_output)
        self.failIf(table_output.find('<td>%s</td>' % hidden_input_elem) == -1,
            'Hidden input element is not enclosed in <td> element.')

class ChildAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    def queryset(self, request):
        return super(ChildAdmin, self).queryset(request).select_related("parent__name")

class MockRequest(object):
    GET = {}
