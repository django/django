from django.db.models import signals
from django.test import TestCase
from modeltests.signals.models import Person

class MyReceiver(object):
    def __init__(self, param):
        self.param = param
        self._run = False

    def __call__(self, signal, sender, **kwargs):
        self._run = True
        signal.disconnect(receiver=self, sender=sender)

class SignalTests(TestCase):
    def test_disconnect_in_dispatch(self):
        """
        Test that signals that disconnect when being called don't mess future
        dispatching.
        """
        a, b = MyReceiver(1), MyReceiver(2)
        signals.post_save.connect(sender=Person, receiver=a)
        signals.post_save.connect(sender=Person, receiver=b)
        p = Person.objects.create(first_name='John', last_name='Smith')
        
        self.failUnless(a._run)
        self.failUnless(b._run)
        self.assertEqual(signals.post_save.receivers, [])
        
