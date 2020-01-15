import datetime

from django.core import signing
from django.test import SimpleTestCase
from django.test.utils import freeze_time


class TestSigner(SimpleTestCase):

    def test_signature(self):
        "signature() method should generate a signature"
        signer = signing.Signer('predictable-secret', algorithm='sha1')
        signer2 = signing.Signer('predictable-secret2', algorithm='sha1')
        for s in (
            b'hello',
            b'3098247:529:087:',
            '\u2019'.encode(),
        ):
            self.assertEqual(
                signer.signature(s),
                signing.base64_hmac(signer.salt + 'signer', s, 'predictable-secret')
            )
            self.assertNotEqual(signer.signature(s), signer2.signature(s))

    def test_signature_with_salt(self):
        "signature(value, salt=...) should work"
        signer = signing.Signer('predictable-secret', salt='extra-salt', algorithm='sha1')
        self.assertEqual(
            signer.signature('hello'),
            signing.base64_hmac('extra-salt' + 'signer', 'hello', 'predictable-secret')
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
        for example in examples:
            signed = signer.sign(example)
            self.assertIsInstance(signed, str)
            self.assertNotEqual(example, signed)
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

    def test_invalid_algorithm(self):
        signer = signing.Signer('predictable-secret')
        msg = 'The signature algorithm "md5" is not supported.'
        with self.assertRaisesMessage(signing.BadSignature, msg):
            signer.unsign('foo:md5:asdj*+Vcfd7==fDsj')

    def test_dumps_loads(self):
        "dumps and loads be reversible for any JSON serializable object"
        objects = [
            ['a', 'list'],
            'a string \u2019',
            {'a': 'dictionary'},
        ]
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
        self.assertEqual(
            'foo:blake2b:mNILqGpg-VOoLx5NwQHWoMRcwLo6r66KOf1HVzrnCnQtzTVCjzAFx8'
            'B6Trug8f3iCmqUhx7jRLH4R6oyJlimwA',
            s.sign('foo')
        )

    def test_valid_sep(self):
        separators = ['/', '*sep*', ',']
        for sep in separators:
            signer = signing.Signer('predictable-secret', sep=sep)
            self.assertEqual(
                'foo{sep}blake2b{sep}xyU6Jtu428RBakSkDumWwGOrOJtaqe9MHZZ7h_VotL'
                'gQbPv_kGpAfxsznsF-ixM2vHiY3-BM3bvbaR6gbnwOqw'.format(sep=sep),
                signer.sign('foo')
            )

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

    def test_legacy_format_unsign(self):
        """
        During a deprecation period, Django accepts the legacy signed value
        without any specified algorithm.
        """
        signer = signing.TimestampSigner('predictable-key')
        self.assertEqual(signer.unsign('hello:1iroxj:SmBeiMT9ltZ4inOu1S_JVlz8PT8'), 'hello')
