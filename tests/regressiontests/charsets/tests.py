import re

from django.test import Client, TestCase
from django.conf import settings
from django.http.charsets import get_response_encoding, get_codec


CHARSET_RE = re.compile('.*; charset=([\w\d-]+);?')
def get_charset(response):
    match = CHARSET_RE.match(response.get("content-type",""))
    if match:
        charset = match.group(1)
    else:
        charset = None
    return charset

class ClientTest(TestCase):
    urls = 'regressiontests.charsets.urls'
    test_string = u'\u82cf\u8054\u961f'
    codec = get_codec("GBK")

    def encode(self, string):
        return self.codec.encode(string)[0]

    def decode(self, string):
        return self.codec.decode(string)[0]

    def test_good_accept_charset(self):
        "Use Accept-Charset, with a quality value that throws away default_charset"
        # The data is ignored, but let's check it doesn't crash the system
        # anyway.

        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="ascii,utf-8;q=0")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_charset(response), "ascii")
    
    def test_quality_sorting_wildcard_wins(self):
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="us;q=0.8,*;q=0.9")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_charset(response), settings.DEFAULT_CHARSET)
    
    def test_quality_sorting_wildcard_loses_alias_wins(self):
        # us is an alias for ascii
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="us;q=0.8,*;q=0.7")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_charset(response), "us")
    
    def test_quality_sorting(self):
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="ascii;q=0.89,utf-8;q=.9")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_charset(response), settings.DEFAULT_CHARSET)
    
    def test_fallback_charset(self):
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="utf-8;q=0")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_charset(response), "ISO-8859-1")  
        
    def test_bad_accept_charset(self):
        "Do not use a charset that Python does not support"

        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="Huttese")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_charset(response), "utf-8")

    def test_force_no_charset(self):
        "If we have no accepted charsets that we have codecs for, 406"
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="utf-8;q=0,*;q=0")

        self.assertEqual(response.status_code, 406)

    def test_good_content_type(self):
        "Use good content-type"

        response = self.client.post('/good_content_type/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_charset(response), "us")

    def test_bad_content_type(self):
        "Use bad content-type"
        self.assertRaises(Exception, self.client.get, "/bad_content_type/")

    def test_content_type_no_charset(self):
        response = self.client.post('/content_type_no_charset/')
        self.assertEqual(get_charset(response), None)

    def test_determine_charset(self):
        content_type, codec = get_response_encoding("", "utf-8;q=0.8,*;q=0.9")
        self.assertEqual(codec, get_codec("ISO-8859-1"))

    def test_basic_response(self):
        "Make sure a normal request gets the default charset, with a 200 response."
        response = self.client.post('/basic_response/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_charset(response), settings.DEFAULT_CHARSET)

    def test_encode_content_type(self):
        "Make sure a request gets encoded according to the content type in the view."
        response = self.client.post('/encode_response_content_type/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_codec(get_charset(response)).name, self.codec.name)
        self.assertEqual(response.content, self.encode(self.test_string))

    def test_encode_accept_charset(self):
        "Make sure a request gets encoded according to the Accept-Charset request header."
        response = self.client.post('/encode_response_accept_charset/',
                                     ACCEPT_CHARSET="gbk;q=1,utf-8;q=0.9")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_codec(get_charset(response)).name, self.codec.name)
        self.assertEqual(response.content, self.encode(self.test_string))

    def test_bad_codec(self):
        "Assure we get an Exception for setting a bad codec in the view."
        self.assertRaises(Exception, self.client.post, '/bad_codec/')

    def test_good_codecs(self):
        response = self.client.post('/good_codec/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, self.encode(self.test_string))
