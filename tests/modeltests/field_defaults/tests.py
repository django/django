# coding: utf-8
from datetime import datetime

from django.test import TestCase
from django.utils.safestring import SafeUnicode, SafeString

from models import Article

class FieldDefaultsTestCase(TestCase):
    def test_article_defaults(self):
        # No articles are in the system yet.
        self.assertEqual(len(Article.objects.all()), 0)
        
        # Create an Article.
        a = Article(id=None)

        # Grab the current datetime it should be very close to the
        # default that just got saved as a.pub_date
        now = datetime.now()

        # Save it into the database. You have to call save() explicitly.
        a.save()

        # Now it has an ID. Note it's a long integer, as designated by
        # the trailing "L".
        self.assertEqual(a.id, 1L)

        # Access database columns via Python attributes.
        self.assertEqual(a.headline, u'Default headline')

        # make sure the two dates are sufficiently close
        #fixme, use the new unittest2 function
        d = now - a.pub_date
        self.assertTrue(d.seconds < 5)

        # make sure that SafeString/SafeUnicode fields work
        a.headline = SafeUnicode(u'Iñtërnâtiônàlizætiøn1')
        a.save()
        a.headline = SafeString(u'Iñtërnâtiônàlizætiøn1'.encode('utf-8'))
        a.save()
