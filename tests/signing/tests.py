from __future__ import unicode_literals

import datetime

from django.core import signing
from django.test import SimpleTestCase
from django.test.utils import freeze_time
from django.utils import six
from django.utils.encoding import force_str


class TestSigner(SimpleTestCase):

    def test_signature(self):
        "signature() method should generate a signature"
        signer = signing.Signer('predictable-secret')
        signer2 = signing.Signer('predictable-secret2')
        for s in (
            b'hello',
            b'3098247:529:087:',
            '\u2019'.encode('utf-8'),
        ):
            self.assertEqual(
                signer.signature(s),
                signing.base64_hmac(signer.salt + 'signer', s, 'predictable-secret').decode()
            )
            self.assertNotEqual(signer.signature(s), signer2.signature(s))

    def test_signature_with_salt(self):
        "signature(value, salt=...) should work"
        signer = signing.Signer('predictable-secret', salt='extra-salt')
        self.assertEqual(
            signer.signature('hello'),
            signing.base64_hmac('extra-salt' + 'signer', 'hello', 'predictable-secret').decode()
        )
        self.assertNotEqual(
            signing.Signer('predictable-secret', salt='one').signature('hello'),
            signing.Signer('predictable-secret', salt='two').signature('hello'))

    def test_sign_unsign(self):
        "sign/unsign should be reversible"
        signer = signing.Signer('predictable-secret')
        examples = [
            'q;wjmbk;wkmb',
            '3098247529087',
            '3098247:529:087:',
            'jkw osanteuh ,rcuh nthu aou oauh ,ud du',
            '\u2019',
        ]
        if six.PY2:
            examples.append(b'a byte string')
        for example in examples:
            signed = signer.sign(example)
            self.assertIsInstance(signed, str)
            self.assertNotEqual(force_str(example), signed)
            self.assertEqual(example, signer.unsign(signed))

    def test_unsign_detects_tampering(self):
        "unsign should raise an exception if the value has been tampered with"
        signer = signing.Signer('predictable-secret')
        value = 'Another string'
        signed_value = signer.sign(value)
        transforms = (
            lambda s: s.upper(),
            lambda s: s + 'a',
            lambda s: 'a' + s[1:],
            lambda s: s.replace(':', ''),
        )
        self.assertEqual(value, signer.unsign(signed_value))
        for transform in transforms:
            with self.assertRaises(signing.BadSignature):
                signer.unsign(transform(signed_value))

    def test_dumps_loads(self):
        "dumps and loads be reversible for any JSON serializable object"
        objects = [
            ['a', 'list'],
            'a unicode string \u2019',
            {'a': 'dictionary'},
        ]
        if six.PY2:
            objects.append(b'a byte string')
        for o in objects:
            self.assertNotEqual(o, signing.dumps(o))
            self.assertEqual(o, signing.loads(signing.dumps(o)))
            self.assertNotEqual(o, signing.dumps(o, compress=True))
            self.assertEqual(o, signing.loads(signing.dumps(o, compress=True)))

    def test_decode_detects_tampering(self):
        "loads should raise exception for tampered objects"
        transforms = (
            lambda s: s.upper(),
            lambda s: s + 'a',
            lambda s: 'a' + s[1:],
            lambda s: s.replace(':', ''),
        )
        value = {
            'foo': 'bar',
            'baz': 1,
        }
        encoded = signing.dumps(value)
        self.assertEqual(value, signing.loads(encoded))
        for transform in transforms:
            with self.assertRaises(signing.BadSignature):
                signing.loads(transform(encoded))

    def test_works_with_non_ascii_keys(self):
        binary_key = b'\xe7'  # Set some binary (non-ASCII key)

        s = signing.Signer(binary_key)
        self.assertEqual('foo:6NB0fssLW5RQvZ3Y-MTerq2rX7w', s.sign('foo'))

    def test_valid_sep(self):
        separators = ['/', '*sep*', ',']
        for sep in separators:
            signer = signing.Signer('predictable-secret', sep=sep)
            self.assertEqual('foo%ssH9B01cZcJ9FoT_jEVkRkNULrl8' % sep, signer.sign('foo'))

    def test_invalid_sep(self):
        """should warn on invalid separator"""
        msg = 'Unsafe Signer separator: %r (cannot be empty or consist of only A-z0-9-_=)'
        separators = ['', '-', 'abc']
        for sep in separators:
            with self.assertRaisesMessage(ValueError, msg % sep):
                signing.Signer(sep=sep)


class TestTimestampSigner(SimpleTestCase):

    def test_timestamp_signer(self):
        value = 'hello'
        with freeze_time(123456789):
            signer = signing.TimestampSigner('predictable-key')
            ts = signer.sign(value)
            self.assertNotEqual(ts, signing.Signer('predictable-key').sign(value))
            self.assertEqual(signer.unsign(ts), value)

        with freeze_time(123456800):
            self.assertEqual(signer.unsign(ts, max_age=12), value)
            # max_age parameter can also accept a datetime.timedelta object
            self.assertEqual(signer.unsign(ts, max_age=datetime.timedelta(seconds=11)), value)
            with self.assertRaises(signing.SignatureExpired):
                signer.unsign(ts, max_age=10)
