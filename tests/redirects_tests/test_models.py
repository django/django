from django.contrib.redirects.models import Redirect
from django.test import SimpleTestCase


class RedirectTests(SimpleTestCase):
    def test_str_representation(self):
        r = Redirect(
            domain='test.loc',
            old_path='/initial',
            new_path='/new_target'
        )

        self.assertEqual(str(r), 'test.loc/initial ---> /new_target')
