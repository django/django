from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from models import *

class GenericRelationTests(TestCase):

    def test_inherited_models_content_type(self):
        """
        Test that GenericRelations on inherited classes use the correct content
        type.
        """

        p = Place.objects.create(name="South Park")
        r = Restaurant.objects.create(name="Chubby's")
        l1 = Link.objects.create(content_object=p)
        l2 = Link.objects.create(content_object=r)
        self.assertEqual(list(p.links.all()), [l1])
        self.assertEqual(list(r.links.all()), [l2])

    def test_reverse_relation_pk(self):
        """
        Test that the correct column name is used for the primary key on the
        originating model of a query.  See #12664.
        """
        p = Person.objects.create(account=23, name='Chef')
        a = Address.objects.create(street='123 Anywhere Place',
                                   city='Conifer', state='CO',
                                   zipcode='80433', content_object=p)

        qs = Person.objects.filter(addresses__zipcode='80433')
        self.assertEqual(1, qs.count())
        self.assertEqual('Chef', qs[0].name)

    def test_charlink_delete(self):
        oddrel = OddRelation1.objects.create(name='clink')
        cl = CharLink.objects.create(content_object=oddrel)
        oddrel.delete()

    def test_textlink_delete(self):
        oddrel = OddRelation2.objects.create(name='tlink')
        tl = TextLink.objects.create(content_object=oddrel)
        oddrel.delete()

    def test_q_object_or(self):
        """
        Tests that SQL query parameters for generic relations are properly
        grouped when OR is used.

        Test for bug http://code.djangoproject.com/ticket/11535

        In this bug the first query (below) works while the second, with the
        query parameters the same but in reverse order, does not.

        The issue is that the generic relation conditions do not get properly
        grouped in parentheses.
        """
        note_contact = Contact.objects.create()
        org_contact = Contact.objects.create()
        note = Note.objects.create(note='note', content_object=note_contact)
        org = Organization.objects.create(name='org name')
        org.contacts.add(org_contact)
        # search with a non-matching note and a matching org name
        qs = Contact.objects.filter(Q(notes__note__icontains=r'other note') |
                            Q(organizations__name__icontains=r'org name'))
        self.assertTrue(org_contact in qs)
        # search again, with the same query parameters, in reverse order
        qs = Contact.objects.filter(
            Q(organizations__name__icontains=r'org name') |
            Q(notes__note__icontains=r'other note'))
        self.assertTrue(org_contact in qs)



