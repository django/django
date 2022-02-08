from django.db.models import Q
from django.test import TestCase

from .models import Issue, StringReferenceModel, User


class RelatedObjectTests(TestCase):
    def test_related_objects_have_name_attribute(self):
        for field_name in ("test_issue_client", "test_issue_cc"):
            obj = User._meta.get_field(field_name)
            self.assertEqual(field_name, obj.field.related_query_name())

    def test_m2m_and_m2o(self):
        r = User.objects.create(username="russell")
        g = User.objects.create(username="gustav")

        i1 = Issue(num=1)
        i1.client = r
        i1.save()

        i2 = Issue(num=2)
        i2.client = r
        i2.save()
        i2.cc.add(r)

        i3 = Issue(num=3)
        i3.client = g
        i3.save()
        i3.cc.add(r)

        self.assertQuerysetEqual(
            Issue.objects.filter(client=r.id),
            [
                1,
                2,
            ],
            lambda i: i.num,
        )
        self.assertQuerysetEqual(
            Issue.objects.filter(client=g.id),
            [
                3,
            ],
            lambda i: i.num,
        )
        self.assertQuerysetEqual(Issue.objects.filter(cc__id__exact=g.id), [])
        self.assertQuerysetEqual(
            Issue.objects.filter(cc__id__exact=r.id),
            [
                2,
                3,
            ],
            lambda i: i.num,
        )

        # These queries combine results from the m2m and the m2o relationships.
        # They're three ways of saying the same thing.
        self.assertQuerysetEqual(
            Issue.objects.filter(Q(cc__id__exact=r.id) | Q(client=r.id)),
            [
                1,
                2,
                3,
            ],
            lambda i: i.num,
        )
        self.assertQuerysetEqual(
            Issue.objects.filter(cc__id__exact=r.id)
            | Issue.objects.filter(client=r.id),
            [
                1,
                2,
                3,
            ],
            lambda i: i.num,
        )
        self.assertQuerysetEqual(
            Issue.objects.filter(Q(client=r.id) | Q(cc__id__exact=r.id)),
            [
                1,
                2,
                3,
            ],
            lambda i: i.num,
        )


class RelatedObjectUnicodeTests(TestCase):
    def test_m2m_with_unicode_reference(self):
        """
        Regression test for #6045: references to other models can be
        strings, providing they are directly convertible to ASCII.
        """
        m1 = StringReferenceModel.objects.create()
        m2 = StringReferenceModel.objects.create()
        m2.others.add(m1)  # used to cause an error (see ticket #6045)
        m2.save()
        list(m2.others.all())  # Force retrieval.
