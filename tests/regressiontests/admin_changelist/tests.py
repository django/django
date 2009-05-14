import unittest 
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from regressiontests.admin_changelist.models import Child

class ChangeListTests(unittest.TestCase):
    def test_select_related_preserved(self):
        """
        Regression test for #10348: ChangeList.get_query_set() shouldn't
        overwrite a custom select_related provided by ModelAdmin.queryset().
        """
        m = ChildAdmin(Child, admin.site)
        cl = ChangeList(MockRequest(), Child, m.list_display, m.list_display_links, 
                m.list_filter,m.date_hierarchy, m.search_fields, 
                m.list_select_related, m.list_per_page, m.list_editable, m)
        self.assertEqual(cl.query_set.query.select_related, {'parent': {'name': {}}})

class ChildAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    def queryset(self, request):
        return super(ChildAdmin, self).queryset(request).select_related("parent__name")

class MockRequest(object):
    GET = {}
