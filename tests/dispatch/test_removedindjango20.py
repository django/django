import warnings

from django.dispatch import Signal
from django.test import SimpleTestCase

a_signal = Signal(providing_args=['val'])


def receiver_1_arg(val, **kwargs):
    return val


class DispatcherTests(SimpleTestCase):

    def test_disconnect_weak_deprecated(self):
        a_signal.connect(receiver_1_arg)
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            a_signal.disconnect(receiver_1_arg, weak=True)
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            'Passing `weak` to disconnect has no effect.',
        )
