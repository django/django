from thibaud.test import SimpleTestCase
from thibaud.test.client import FakePayload


class FakePayloadTests(SimpleTestCase):
    def test_write_after_read(self):
        payload = FakePayload()
        for operation in [payload.read, payload.readline]:
            with self.subTest(operation=operation.__name__):
                operation()
                msg = "Unable to write a payload after it's been read"
                with self.assertRaisesMessage(ValueError, msg):
                    payload.write(b"abc")
