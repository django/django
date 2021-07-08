from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import City, State


@override_settings(ROOT_URLCONF='admin_views.urls')
class AdminHistoryViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username='super', password='secret', email='super@example.com',
        )

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_changed_message_uses_form_labels(self):
        """
        Admin's model history change messages use form labels instead of
        field names.
        """
        state = State.objects.create(name='My State Name')
        city = City.objects.create(name='My City Name', state=state)
        change_dict = {
            'name': 'My State Name 2',
            'nolabel_form_field': True,
            'city_set-0-name': 'My City name 2',
            'city_set-0-id': city.pk,
            'city_set-TOTAL_FORMS': '3',
            'city_set-INITIAL_FORMS': '1',
            'city_set-MAX_NUM_FORMS': '0',
        }
        state_change_url = reverse('admin:admin_views_state_change', args=(state.pk,))
        self.client.post(state_change_url, change_dict)
        logentry = LogEntry.objects.filter(content_type__model__iexact='state').latest('id')
        self.assertEqual(
            logentry.get_change_message(),
            'Changed State name (from form’s Meta.labels), '
            'nolabel_form_field and not_a_form_field. '
            'Changed City verbose_name for city “%s”.' % city
        )
