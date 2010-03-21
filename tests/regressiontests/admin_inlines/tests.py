from django.test import TestCase

# local test models
from models import Holder, Inner, InnerInline
from models import Holder2, Inner2, Holder3, Inner3

class TestInline(TestCase):
    fixtures = ['admin-views-users.xml']

    def setUp(self):
        holder = Holder(dummy=13)
        holder.save()
        Inner(dummy=42, holder=holder).save()
        self.change_url = '/test_admin/admin/admin_inlines/holder/%i/' % holder.id

        result = self.client.login(username='super', password='secret')
        self.failUnlessEqual(result, True)

    def tearDown(self):
        self.client.logout()

    def test_can_delete(self):
        """
        can_delete should be passed to inlineformset factory.
        """
        response = self.client.get(self.change_url)
        inner_formset = response.context[-1]['inline_admin_formsets'][0].formset
        expected = InnerInline.can_delete
        actual = inner_formset.can_delete
        self.assertEqual(expected, actual, 'can_delete must be equal')

class TestInlineMedia(TestCase):
    fixtures = ['admin-views-users.xml']

    def setUp(self):

        result = self.client.login(username='super', password='secret')
        self.failUnlessEqual(result, True)

    def tearDown(self):
        self.client.logout()

    def test_inline_media_only_base(self):
        holder = Holder(dummy=13)
        holder.save()
        Inner(dummy=42, holder=holder).save()
        change_url = '/test_admin/admin/admin_inlines/holder/%i/' % holder.id
        response = self.client.get(change_url)
        self.assertContains(response, 'my_awesome_admin_scripts.js')

    def test_inline_media_only_inline(self):
        holder = Holder3(dummy=13)
        holder.save()
        Inner3(dummy=42, holder=holder).save()
        change_url = '/test_admin/admin/admin_inlines/holder3/%i/' % holder.id
        response = self.client.get(change_url)
        self.assertContains(response, 'my_awesome_inline_scripts.js')

    def test_all_inline_media(self):
        holder = Holder2(dummy=13)
        holder.save()
        Inner2(dummy=42, holder=holder).save()
        change_url = '/test_admin/admin/admin_inlines/holder2/%i/' % holder.id
        response = self.client.get(change_url)
        self.assertContains(response, 'my_awesome_admin_scripts.js')
        self.assertContains(response, 'my_awesome_inline_scripts.js')