import time

from django.core import signing
from django.test import TestCase
from django.utils.encoding import force_unicode


class TestSigner(TestCase):

    def test_signature(self):
        "signature() method should generate a signature"
        signer = signing.Signer('predictable-secret')
        signer2 = signing.Signer('predictable-secret2')
        for s in (
            'hello',
            '3098247:529:087:',
            u'\u2019'.encode('utf-8'),
        ):
            self.assertEqual(
                signer.signature(s),
                signing.base64_hmac(signer.salt + 'signer', s,
                    'predictable-secret')
            )
            self.assertNotEqual(signer.signature(s), signer2.signature(s))

    def test_signature_with_salt(self):
        "signature(value, salt=...) should work"
        signer = signing.Signer('predictable-secret', salt='extra-salt')
        self.assertEqual(
            signer.signature('hello'),
                signing.base64_hmac('extra-salt' + 'signer',
                'hello', 'predictable-secret'))
        self.assertNotEqual(
            signing.Signer('predictable-secret', salt='one').signature('hello'),
            signing.Signer('predictable-secret', salt='two').signature('hello'))

    def test_sign_unsign(self):
        "sign/unsign should be reversible"
        signer = signing.Signer('predictable-secret')
        examples = (
            'q;wjmbk;wkmb',
            '3098247529087',
            '3098247:529:087:',
            'jkw osanteuh ,rcuh nthu aou oauh ,ud du',
            u'\u2019',
        )
        for example in examples:
            self.assertNotEqual(
                force_unicode(example), force_unicode(signer.sign(example)))
            self.assertEqual(example, signer.unsign(signer.sign(example)))

    def unsign_detects_tampering(self):
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
            self.assertRaises(
                signing.BadSignature, signer.unsign, transform(signed_value))

    def test_dumps_loads(self):
        "dumps and loads be reversible for any JSON serializable object"
        objects = (
            ['a', 'list'],
            'a string',
            u'a unicode string \u2019',
            {'a': 'dictionary'},
        )
        for o in objects:
            self.assertNotEqual(o, signing.dumps(o))
            self.assertEqual(o, signing.loads(signing.dumps(o)))

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
            self.assertRaises(
                signing.BadSignature, signing.loads, transform(encoded))

class TestTimestampSigner(TestCase):

    def test_timestamp_signer(self):
        value = u'hello'
        _time = time.time
        time.time = lambda: 123456789
        try:
            signer = signing.TimestampSigner('predictable-key')
            ts = signer.sign(value)
            self.assertNotEqual(ts,
                signing.Signer('predictable-key').sign(value))

            self.assertEqual(signer.unsign(ts), value)
            time.time = lambda: 123456800
            self.assertEqual(signer.unsign(ts, max_age=12), value)
            self.assertEqual(signer.unsign(ts, max_age=11), value)
            self.assertRaises(
                signing.SignatureExpired, signer.unsign, ts, max_age=10)
        finally:
            time.time = _time
