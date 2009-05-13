from django.forms.models import inlineformset_factory
from django.test import TestCase

from models import User, UserSite

class InlineFormsetTests(TestCase):
    def test_formset_over_to_field(self):
        "A formset over a ForeignKey with a to_field can be saved. Regression for #10243"
        FormSet = inlineformset_factory(User, UserSite)
        user = User.objects.create(serial=1, username='apollo13')
        user.save()
        data = {
            'usersite_set-TOTAL_FORMS': u'1',
            'usersite_set-INITIAL_FORMS': u'0',
            'usersite_set-0-data': u'10',
            'usersite_set-0-user': u'apollo13'
        }
        form_set = FormSet(data, instance=user)
        if form_set.is_valid():
            form_set.save()
            usersite = UserSite.objects.all().values()[0]
            self.assertEqual(usersite, {'data': 10, 'user_id': u'apollo13', 'id': 1})
        else:
            self.fail('Errors found on form:%s' % form_set.errors)