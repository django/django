# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.test import TestCase
from .models import Foo, Whiz, Bar, Article, Base, Child


class StringLookupTests(TestCase):

    def test_string_form_referencing(self):
        """
        Regression test for #1661 and #1662

        Check that string form referencing of
        models works, both as pre and post reference, on all RelatedField types.
        """

        f1 = Foo(name="Foo1")
        f1.save()
        f2 = Foo(name="Foo2")
        f2.save()

        w1 = Whiz(name="Whiz1")
        w1.save()

        b1 = Bar(name="Bar1", normal=f1, fwd=w1, back=f2)
        b1.save()

        self.assertEqual(b1.normal, f1)

        self.assertEqual(b1.fwd, w1)

        self.assertEqual(b1.back, f2)

        base1 = Base(name="Base1")
        base1.save()

        child1 = Child(name="Child1", parent=base1)
        child1.save()

        self.assertEqual(child1.parent, base1)

    def test_unicode_chars_in_queries(self):
        """
        Regression tests for #3937

        make sure we can use unicode characters in queries.
        If these tests fail on MySQL, it's a problem with the test setup.
        A properly configured UTF-8 database can handle this.
        """

        fx = Foo(name='Bjorn', friend='François')
        fx.save()
        self.assertEqual(Foo.objects.get(friend__contains='\xe7'), fx)

        # We can also do the above query using UTF-8 strings.
        self.assertEqual(Foo.objects.get(friend__contains=b'\xc3\xa7'), fx)

    def test_queries_on_textfields(self):
        """
        Regression tests for #5087

        make sure we can perform queries on TextFields.
        """

        a = Article(name='Test', text='The quick brown fox jumps over the lazy dog.')
        a.save()
        self.assertEqual(Article.objects.get(text__exact='The quick brown fox jumps over the lazy dog.'), a)

        self.assertEqual(Article.objects.get(text__contains='quick brown fox'), a)

    def test_ipaddress_on_postgresql(self):
        """
        Regression test for #708

        "like" queries on IP address fields require casting to text (on PostgreSQL).
        """
        a = Article(name='IP test', text='The body', submitted_from='192.0.2.100')
        a.save()
        self.assertEqual(repr(Article.objects.filter(submitted_from__contains='192.0.2')),
            repr([a]))
