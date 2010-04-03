from django.test import TestCase

from models import A, B, D

class SimpleTest(TestCase):
    def setUp(self):
        self.a1 = A.objects.create()
        self.a2 = A.objects.create()
        for x in range(20):
            B.objects.create(a=self.a1)
            D.objects.create(a=self.a1)

    def test_nonempty_update(self):
        """
        Test that update changes the right number of rows for a nonempty queryset
        """
        num_updated = self.a1.b_set.update(y=100)
        self.failUnlessEqual(num_updated, 20)
        cnt = B.objects.filter(y=100).count()
        self.failUnlessEqual(cnt, 20)

    def test_empty_update(self):
        """
        Test that update changes the right number of rows for an empty queryset
        """
        num_updated = self.a2.b_set.update(y=100)
        self.failUnlessEqual(num_updated, 0)
        cnt = B.objects.filter(y=100).count()
        self.failUnlessEqual(cnt, 0)

    def test_nonempty_update_with_inheritance(self):
        """
        Test that update changes the right number of rows for an empty queryset
        when the update affects only a base table
        """
        num_updated = self.a1.d_set.update(y=100)
        self.failUnlessEqual(num_updated, 20)
        cnt = D.objects.filter(y=100).count()
        self.failUnlessEqual(cnt, 20)

    def test_empty_update_with_inheritance(self):
        """
        Test that update changes the right number of rows for an empty queryset
        when the update affects only a base table
        """
        num_updated = self.a2.d_set.update(y=100)
        self.failUnlessEqual(num_updated, 0)
        cnt = D.objects.filter(y=100).count()
        self.failUnlessEqual(cnt, 0)
