from unittest import TestCase, expectedFailure


class FailureTestCase(TestCase):
    def test_sample(self):
        self.assertEqual(0, 1)


class ErrorTestCase(TestCase):
    def test_sample(self):
        raise Exception("test")


class ExpectedFailureTestCase(TestCase):
    @expectedFailure
    def test_sample(self):
        self.assertEqual(0, 1)


class UnexpectedSuccessTestCase(TestCase):
    @expectedFailure
    def test_sample(self):
        self.assertEqual(1, 1)
