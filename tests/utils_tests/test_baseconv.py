from unittest import TestCase

from django.utils.baseconv import (
    BaseConverter, base2, base16, base36, base56, base62, base64,
)
from django.utils.six.moves import range


class TestBaseConv(TestCase):

    def test_baseconv(self):
        nums = [-10 ** 10, 10 ** 10] + list(range(-100, 100))
        for converter in [base2, base16, base36, base56, base62, base64]:
            for i in nums:
                self.assertEqual(i, converter.decode(converter.encode(i)))

    def test_base11(self):
        base11 = BaseConverter('0123456789-', sign='$')
        self.assertEqual(base11.encode(1234), '-22')
        self.assertEqual(base11.decode('-22'), 1234)
        self.assertEqual(base11.encode(-1234), '$-22')
        self.assertEqual(base11.decode('$-22'), -1234)

    def test_base20(self):
        base20 = BaseConverter('0123456789abcdefghij')
        self.assertEqual(base20.encode(1234), '31e')
        self.assertEqual(base20.decode('31e'), 1234)
        self.assertEqual(base20.encode(-1234), '-31e')
        self.assertEqual(base20.decode('-31e'), -1234)

    def test_base64(self):
        self.assertEqual(base64.encode(1234), 'JI')
        self.assertEqual(base64.decode('JI'), 1234)
        self.assertEqual(base64.encode(-1234), '$JI')
        self.assertEqual(base64.decode('$JI'), -1234)

    def test_base7(self):
        base7 = BaseConverter('cjdhel3', sign='g')
        self.assertEqual(base7.encode(1234), 'hejd')
        self.assertEqual(base7.decode('hejd'), 1234)
        self.assertEqual(base7.encode(-1234), 'ghejd')
        self.assertEqual(base7.decode('ghejd'), -1234)

    def test_exception(self):
        with self.assertRaises(ValueError):
            BaseConverter('abc', sign='a')
        self.assertIsInstance(BaseConverter('abc', sign='d'), BaseConverter)
