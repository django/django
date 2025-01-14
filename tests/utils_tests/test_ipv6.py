import traceback
from decimal import Decimal
from io import StringIO
from ipaddress import IPv6Address

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils.ipv6 import (
    MAX_IPV6_ADDRESS_LENGTH,
    clean_ipv6_address,
    is_valid_ipv6_address,
)


class TestUtilsIPv6(SimpleTestCase):
    def test_validates_correct_plain_address(self):
        self.assertTrue(is_valid_ipv6_address("fe80::223:6cff:fe8a:2e8a"))
        self.assertTrue(is_valid_ipv6_address("2a02::223:6cff:fe8a:2e8a"))
        self.assertTrue(is_valid_ipv6_address("1::2:3:4:5:6:7"))
        self.assertTrue(is_valid_ipv6_address("::"))
        self.assertTrue(is_valid_ipv6_address("::a"))
        self.assertTrue(is_valid_ipv6_address("2::"))

    def test_validates_correct_with_v4mapping(self):
        self.assertTrue(is_valid_ipv6_address("::ffff:254.42.16.14"))
        self.assertTrue(is_valid_ipv6_address("::ffff:0a0a:0a0a"))

    def test_validates_correct_with_ipv6_instance(self):
        cases = [
            IPv6Address("::ffff:2.125.160.216"),
            IPv6Address("fe80::1"),
            IPv6Address("::"),
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertIs(is_valid_ipv6_address(case), True)

    def test_validates_incorrect_plain_address(self):
        self.assertFalse(is_valid_ipv6_address("foo"))
        self.assertFalse(is_valid_ipv6_address("127.0.0.1"))
        self.assertFalse(is_valid_ipv6_address("12345::"))
        self.assertFalse(is_valid_ipv6_address("1::2:3::4"))
        self.assertFalse(is_valid_ipv6_address("1::zzz"))
        self.assertFalse(is_valid_ipv6_address("1::2:3:4:5:6:7:8"))
        self.assertFalse(is_valid_ipv6_address("1:2"))
        self.assertFalse(is_valid_ipv6_address("1:::2"))
        self.assertFalse(is_valid_ipv6_address("fe80::223: 6cff:fe8a:2e8a"))
        self.assertFalse(is_valid_ipv6_address("2a02::223:6cff :fe8a:2e8a"))

    def test_validates_incorrect_with_v4mapping(self):
        self.assertFalse(is_valid_ipv6_address("::ffff:999.42.16.14"))
        self.assertFalse(is_valid_ipv6_address("::ffff:zzzz:0a0a"))
        # The ::1.2.3.4 format used to be valid but was deprecated
        # in RFC 4291 section 2.5.5.1.
        self.assertTrue(is_valid_ipv6_address("::254.42.16.14"))
        self.assertTrue(is_valid_ipv6_address("::0a0a:0a0a"))
        self.assertFalse(is_valid_ipv6_address("::999.42.16.14"))
        self.assertFalse(is_valid_ipv6_address("::zzzz:0a0a"))

    def test_validates_incorrect_with_non_string(self):
        cases = [None, [], {}, (), Decimal("2.46"), 192.168, 42]
        for case in cases:
            with self.subTest(case=case):
                self.assertIs(is_valid_ipv6_address(case), False)

    def test_cleans_plain_address(self):
        self.assertEqual(clean_ipv6_address("DEAD::0:BEEF"), "dead::beef")
        self.assertEqual(
            clean_ipv6_address("2001:000:a:0000:0:fe:fe:beef"), "2001:0:a::fe:fe:beef"
        )
        self.assertEqual(
            clean_ipv6_address("2001::a:0000:0:fe:fe:beef"), "2001:0:a::fe:fe:beef"
        )

    def test_cleans_with_v4_mapping(self):
        self.assertEqual(clean_ipv6_address("::ffff:0a0a:0a0a"), "::ffff:10.10.10.10")
        self.assertEqual(clean_ipv6_address("::ffff:1234:1234"), "::ffff:18.52.18.52")
        self.assertEqual(clean_ipv6_address("::ffff:18.52.18.52"), "::ffff:18.52.18.52")
        self.assertEqual(clean_ipv6_address("::ffff:0.52.18.52"), "::ffff:0.52.18.52")
        self.assertEqual(clean_ipv6_address("::ffff:0.0.0.0"), "::ffff:0.0.0.0")

    def test_unpacks_ipv4(self):
        self.assertEqual(
            clean_ipv6_address("::ffff:0a0a:0a0a", unpack_ipv4=True), "10.10.10.10"
        )
        self.assertEqual(
            clean_ipv6_address("::ffff:1234:1234", unpack_ipv4=True), "18.52.18.52"
        )
        self.assertEqual(
            clean_ipv6_address("::ffff:18.52.18.52", unpack_ipv4=True), "18.52.18.52"
        )

    def test_address_too_long(self):
        addresses = [
            "0000:0000:0000:0000:0000:ffff:192.168.100.228",  # IPv4-mapped IPv6 address
            "0000:0000:0000:0000:0000:ffff:192.168.100.228%123456",  # % scope/zone
            "fe80::223:6cff:fe8a:2e8a:1234:5678:00000",  # MAX_IPV6_ADDRESS_LENGTH + 1
        ]
        msg = "This is the error message."
        value_error_msg = "Unable to convert %s to an IPv6 address (value too long)."
        for addr in addresses:
            with self.subTest(addr=addr):
                self.assertGreater(len(addr), MAX_IPV6_ADDRESS_LENGTH)
                self.assertEqual(is_valid_ipv6_address(addr), False)
                with self.assertRaisesMessage(ValidationError, msg) as ctx:
                    clean_ipv6_address(addr, error_message=msg)
                exception_traceback = StringIO()
                traceback.print_exception(ctx.exception, file=exception_traceback)
                self.assertIn(value_error_msg % addr, exception_traceback.getvalue())
