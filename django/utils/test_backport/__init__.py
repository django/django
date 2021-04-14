class BackPortedTestCaseMixin:

    def assertTypedEquals(self, expected, actual):
        """Asserts that both the types and values are the same."""
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected, actual)

    def assertTypedTupleEquals(self, expected, actual):
        """Asserts that both the types and values in the tuples are the same."""
        self.assertTupleEqual(expected, actual)
        self.assertListEqual(list(map(type, expected)), list(map(type, actual)))

    def assertRaisesMessage(self, exc_type, message,
                            callable, *args, **kwargs):
        """Asserts that callable(*args, **kwargs) raises exc_type(message)."""
        try:
            callable(*args, **kwargs)
        except exc_type as e:
            self.assertEqual(message, str(e))
        else:
            self.fail("%s not raised" % exc_type.__name__)
