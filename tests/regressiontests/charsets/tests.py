from django.test import Client, TestCase
import re
from django.conf import settings

CONTENT_TYPE_RE = re.compile('.*; charset=([\w\d-]+);?')


def get_charset(response):
    match = CONTENT_TYPE_RE.match(response.get("content-type",""))
    if match:
        charset = match.group(1)
    else:
        charset = None
    return charset

class ClientTest(TestCase):
    
    def test_good_accept_charset(self):
        "Use Accept-Charset"
        # The data is ignored, but let's check it doesn't crash the system
        # anyway.
        
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="ascii,utf-8;q=0")
        self.assertEqual(get_charset(response), "ascii")
         
        # us is an alias for ascii
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="us;q=0.8,*;q=0.9")
        self.assertEqual(get_charset(response), settings.DEFAULT_CHARSET)
        
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="us;q=0.8,*;q=0.7")
        self.assertEqual(get_charset(response), "us")
        
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="ascii;q=0.89,utf-8;q=.9")
        self.assertEqual(get_charset(response), settings.DEFAULT_CHARSET)
        
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="utf-8;q=0")
        self.assertEqual(get_charset(response), "ISO-8859-1")  
    
    def test_bad_accept_charset(self):
        "Do not use a malformed Accept-Charset"
        # The data is ignored, but let's check it doesn't crash the system
        # anyway.
        
        response = self.client.post('/accept_charset/', ACCEPT_CHARSET="this_is_junk")
        self.assertEqual(get_charset(response), "utf-8")
        
    def test_good_content_type(self):
        "Use content-type"
        # The data is ignored, but let's check it doesn't crash the system
        # anyway.
        
        response = self.client.post('/good_content_type/')
        self.assertEqual(get_charset(response), "us")
        
    def test_bad_content_type(self):
        "Use content-type"
        # The data is ignored, but let's check it doesn't crash the system
        # anyway.
        
        response = self.client.post('/bad_content_type/')