from django.test import TestCase

# local test models
from models import Holder, Inner, InnerInline

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

