from django.test import SimpleTestCase
from django.test.testcases import SerializeMixin


class TestSerializeMixin(SimpleTestCase):
    def test_init_without_lockfile(self):
        msg = (
            "ExampleTests.lockfile isn't set. Set it to a unique value in the "
            "base class."
        )
        with self.assertRaisesMessage(ValueError, msg):

            class ExampleTests(SerializeMixin, SimpleTestCase):
                pass


class TestSerializeMixinUse(SerializeMixin, SimpleTestCase):
    lockfile = __file__

    def test_usage(self):
        # Running this test ensures that the lock/unlock functions have passed.
        pass
