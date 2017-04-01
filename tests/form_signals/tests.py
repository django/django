from django.forms import signals
from django.test import TestCase

from .forms import DogForm, PersonForm


class SignalTest(TestCase):
    def setUp(self):
        self.pre_signals = (
            len(signals.pre_clean.receivers),
            len(signals.post_clean.receivers),
            len(signals.pre_save.receivers),
            len(signals.post_save.receivers),
        )

    def tearDown(self):
        # All our signals got disconnected properly.
        post_signals = (
            len(signals.pre_clean.receivers),
            len(signals.post_clean.receivers),
            len(signals.pre_save.receivers),
            len(signals.post_save.receivers),
        )
        self.assertEqual(self.pre_signals, post_signals)

    def test_form_pre_init_and_post_init(self):
        data = []

        def pre_init_callback(sender, **kwargs):
            if 'data' in kwargs:
                data.append(1)
            else:
                data.append(0)
        signals.pre_init.connect(pre_init_callback)

        def post_init_callback(sender, instance, **kwargs):
            data.append(instance)
        signals.post_init.connect(post_init_callback)

        person = PersonForm({"first_name": "Jiebin", "last_name": "Luo"})
        self.assertEqual(data, [1, person])

    def test_clean_signals(self):
        data = []

        def pre_clean_callback(sender, **kwargs):
            if 'data' in kwargs:
                data.append(1)
            else:
                data.append(0)

        def post_clean_callback(sender, **kwargs):
            if 'cleaned_data' in kwargs:
                data.append(3)
            else:
                data.append(2)

        signals.pre_clean.connect(pre_clean_callback)
        signals.post_clean.connect(post_clean_callback)

        person = PersonForm({"first_name": "Jiebin", "last_name": "Luo"})
        person.is_valid()

        signals.pre_clean.disconnect(pre_clean_callback)
        signals.post_clean.disconnect(post_clean_callback)

        self.assertEqual(data, [1, 3])

    def test_save_signals(self):
        data = []

        def pre_save_callback(sender, **kwargs):
            if 'instance' in kwargs:
                data.append(1)
            else:
                data.append(0)

        def post_save_callback(sender, **kwargs):
            if 'instance' in kwargs:
                data.append(3)
            else:
                data.append(2)

        signals.pre_save.connect(pre_save_callback)
        signals.post_save.connect(post_save_callback)

        dog = DogForm({"name": "bobi"})
        dog.save()

        signals.pre_save.disconnect(pre_save_callback)
        signals.post_save.disconnect(post_save_callback)

        self.assertEqual(data, [1, 3])
