from django.db.models import signals
from django.dispatch import receiver
from django.test import TestCase

from models import Person, Car


# #8285: signals can be any callable
class PostDeleteHandler(object):
    def __init__(self, data):
        self.data = data

    def __call__(self, signal, sender, instance, **kwargs):
        self.data.append(
            (instance, instance.id is None)
        )

class MyReceiver(object):
    def __init__(self, param):
        self.param = param
        self._run = False

    def __call__(self, signal, sender, **kwargs):
        self._run = True
        signal.disconnect(receiver=self, sender=sender)

class SignalTests(TestCase):
    def test_basic(self):
        # Save up the number of connected signals so that we can check at the
        # end that all the signals we register get properly unregistered (#9989)
        pre_signals = (
            len(signals.pre_save.receivers),
            len(signals.post_save.receivers),
            len(signals.pre_delete.receivers),
            len(signals.post_delete.receivers),
        )

        data = []

        def pre_save_test(signal, sender, instance, **kwargs):
            data.append(
                (instance, kwargs.get("raw", False))
            )
        signals.pre_save.connect(pre_save_test)

        def post_save_test(signal, sender, instance, **kwargs):
            data.append(
                (instance, kwargs.get("created"), kwargs.get("raw", False))
            )
        signals.post_save.connect(post_save_test)

        def pre_delete_test(signal, sender, instance, **kwargs):
            data.append(
                (instance, instance.id is None)
            )
        signals.pre_delete.connect(pre_delete_test)

        post_delete_test = PostDeleteHandler(data)
        signals.post_delete.connect(post_delete_test)

        # throw a decorator syntax receiver into the mix
        @receiver(signals.pre_save)
        def pre_save_decorator_test(signal, sender, instance, **kwargs):
            data.append(instance)

        @receiver(signals.pre_save, sender=Car)
        def pre_save_decorator_sender_test(signal, sender, instance, **kwargs):
            data.append(instance)

        p1 = Person(first_name="John", last_name="Smith")
        self.assertEqual(data, [])
        p1.save()
        self.assertEqual(data, [
            (p1, False),
            p1,
            (p1, True, False),
        ])
        data[:] = []

        p1.first_name = "Tom"
        p1.save()
        self.assertEqual(data, [
            (p1, False),
            p1,
            (p1, False, False),
        ])
        data[:] = []

        # Car signal (sender defined)
        c1 = Car(make="Volkswagon", model="Passat")
        c1.save()
        self.assertEqual(data, [
            (c1, False),
            c1,
            c1,
            (c1, True, False),
        ])
        data[:] = []

        # Calling an internal method purely so that we can trigger a "raw" save.
        p1.save_base(raw=True)
        self.assertEqual(data, [
            (p1, True),
            p1,
            (p1, False, True),
        ])
        data[:] = []

        p1.delete()
        self.assertEqual(data, [
            (p1, False),
            (p1, False),
        ])
        data[:] = []

        p2 = Person(first_name="James", last_name="Jones")
        p2.id = 99999
        p2.save()
        self.assertEqual(data, [
            (p2, False),
            p2,
            (p2, True, False),
        ])
        data[:] = []

        p2.id = 99998
        p2.save()
        self.assertEqual(data, [
            (p2, False),
            p2,
            (p2, True, False),
        ])
        data[:] = []

        p2.delete()
        self.assertEqual(data, [
            (p2, False),
            (p2, False)
        ])

        self.assertQuerysetEqual(
            Person.objects.all(), [
                "James Jones",
            ],
            unicode
        )

        signals.post_delete.disconnect(post_delete_test)
        signals.pre_delete.disconnect(pre_delete_test)
        signals.post_save.disconnect(post_save_test)
        signals.pre_save.disconnect(pre_save_test)
        signals.pre_save.disconnect(pre_save_decorator_test)
        signals.pre_save.disconnect(pre_save_decorator_sender_test, sender=Car)

        # Check that all our signals got disconnected properly.
        post_signals = (
            len(signals.pre_save.receivers),
            len(signals.post_save.receivers),
            len(signals.pre_delete.receivers),
            len(signals.post_delete.receivers),
        )
        self.assertEqual(pre_signals, post_signals)

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
