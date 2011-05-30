import datetime

from django.conf import settings
from django.db import backend, connection, transaction, DEFAULT_DB_ALIAS
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from models import (Book, Award, AwardNote, Person, Child, Toy, PlayedWith,
    PlayedWithNote, Contact, Email, Researcher, Food, Eaten,
    Policy, Version, Location, Item)


# Can't run this test under SQLite, because you can't
# get two connections to an in-memory database.
class DeleteLockingTest(TransactionTestCase):
    def setUp(self):
        # Create a second connection to the default database
        conn_settings = settings.DATABASES[DEFAULT_DB_ALIAS]
        self.conn2 = backend.DatabaseWrapper({
            'HOST': conn_settings['HOST'],
            'NAME': conn_settings['NAME'],
            'OPTIONS': conn_settings['OPTIONS'],
            'PASSWORD': conn_settings['PASSWORD'],
            'PORT': conn_settings['PORT'],
            'USER': conn_settings['USER'],
            'TIME_ZONE': settings.TIME_ZONE,
        })

        # Put both DB connections into managed transaction mode
        transaction.enter_transaction_management()
        transaction.managed(True)
        self.conn2._enter_transaction_management(True)

    def tearDown(self):
        # Close down the second connection.
        transaction.leave_transaction_management()
        self.conn2.close()

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_concurrent_delete(self):
        "Deletes on concurrent transactions don't collide and lock the database. Regression for #9479"

        # Create some dummy data
        b1 = Book(id=1, pagecount=100)
        b2 = Book(id=2, pagecount=200)
        b3 = Book(id=3, pagecount=300)
        b1.save()
        b2.save()
        b3.save()

        transaction.commit()

        self.assertEqual(3, Book.objects.count())

        # Delete something using connection 2.
        cursor2 = self.conn2.cursor()
        cursor2.execute('DELETE from delete_regress_book WHERE id=1')
        self.conn2._commit();

        # Now perform a queryset delete that covers the object
        # deleted in connection 2. This causes an infinite loop
        # under MySQL InnoDB unless we keep track of already
        # deleted objects.
        Book.objects.filter(pagecount__lt=250).delete()
        transaction.commit()
        self.assertEqual(1, Book.objects.count())
        transaction.commit()


class DeleteCascadeTests(TestCase):
    def test_generic_relation_cascade(self):
        """
        Django cascades deletes through generic-related objects to their
        reverse relations.

        """
        person = Person.objects.create(name='Nelson Mandela')
        award = Award.objects.create(name='Nobel', content_object=person)
        note = AwardNote.objects.create(note='a peace prize',
                                        award=award)
        self.assertEqual(AwardNote.objects.count(), 1)
        person.delete()
        self.assertEqual(Award.objects.count(), 0)
        # first two asserts are just sanity checks, this is the kicker:
        self.assertEqual(AwardNote.objects.count(), 0)

    def test_fk_to_m2m_through(self):
        """
        If an M2M relationship has an explicitly-specified through model, and
        some other model has an FK to that through model, deletion is cascaded
        from one of the participants in the M2M, to the through model, to its
        related model.

        """
        juan = Child.objects.create(name='Juan')
        paints = Toy.objects.create(name='Paints')
        played = PlayedWith.objects.create(child=juan, toy=paints,
                                           date=datetime.date.today())
        note = PlayedWithNote.objects.create(played=played,
                                             note='the next Jackson Pollock')
        self.assertEqual(PlayedWithNote.objects.count(), 1)
        paints.delete()
        self.assertEqual(PlayedWith.objects.count(), 0)
        # first two asserts just sanity checks, this is the kicker:
        self.assertEqual(PlayedWithNote.objects.count(), 0)

    def test_15776(self):
        policy = Policy.objects.create(pk=1, policy_number="1234")
        version = Version.objects.create(policy=policy)
        location = Location.objects.create(version=version)
        item = Item.objects.create(version=version, location=location)
        policy.delete()


class DeleteCascadeTransactionTests(TransactionTestCase):
    def test_inheritance(self):
        """
        Auto-created many-to-many through tables referencing a parent model are
        correctly found by the delete cascade when a child of that parent is
        deleted.

        Refs #14896.
        """
        r = Researcher.objects.create()
        email = Email.objects.create(
            label="office-email", email_address="carl@science.edu"
        )
        r.contacts.add(email)

        email.delete()

    def test_to_field(self):
        """
        Cascade deletion works with ForeignKey.to_field set to non-PK.

        """
        apple = Food.objects.create(name="apple")
        eaten = Eaten.objects.create(food=apple, meal="lunch")

        apple.delete()

class LargeDeleteTests(TestCase):
    def test_large_deletes(self):
        "Regression for #13309 -- if the number of objects > chunk size, deletion still occurs"
        for x in range(300):
            track = Book.objects.create(pagecount=x+100)
        Book.objects.all().delete()
        self.assertEqual(Book.objects.count(), 0)
