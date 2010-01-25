import datetime
import pickle

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connections, router, DEFAULT_DB_ALIAS
from django.db.utils import ConnectionRouter
from django.test import TestCase

from models import Book, Person, Review, UserProfile

try:
    # we only have these models if the user is using multi-db, it's safe the
    # run the tests without them though.
    from models import Article, article_using
except ImportError:
    pass

class QueryTestCase(TestCase):
    multi_db = True

    def test_db_selection(self):
        "Check that querysets will use the default databse by default"
        self.assertEquals(Book.objects.db, DEFAULT_DB_ALIAS)
        self.assertEquals(Book.objects.all().db, DEFAULT_DB_ALIAS)

        self.assertEquals(Book.objects.using('other').db, 'other')

        self.assertEquals(Book.objects.db_manager('other').db, 'other')
        self.assertEquals(Book.objects.db_manager('other').all().db, 'other')

    def test_default_creation(self):
        "Objects created on the default database don't leak onto other databases"
        # Create a book on the default database using create()
        Book.objects.create(title="Pro Django",
                            published=datetime.date(2008, 12, 16))

        # Create a book on the default database using a save
        dive = Book()
        dive.title="Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save()

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )

        try:
            Book.objects.get(title="Dive into Python")
            Book.objects.using('default').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Dive into Python"
        )


    def test_other_creation(self):
        "Objects created on another database don't leak onto the default database"
        # Create a book on the second database
        Book.objects.using('other').create(title="Pro Django",
                                           published=datetime.date(2008, 12, 16))

        # Create a book on the default database using a save
        dive = Book()
        dive.title="Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save(using='other')

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Pro Django"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Pro Django"
        )

        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Dive into Python"
        )

    def test_basic_queries(self):
        "Queries are constrained to a single database"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        dive =  Book.objects.using('other').get(published=datetime.date(2009, 5, 4))
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, published=datetime.date(2009, 5, 4))

        dive = Book.objects.using('other').get(title__icontains="dive")
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, title__icontains="dive")

        dive = Book.objects.using('other').get(title__iexact="dive INTO python")
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, title__iexact="dive INTO python")

        dive =  Book.objects.using('other').get(published__year=2009)
        self.assertEqual(dive.title, "Dive into Python")
        self.assertEqual(dive.published, datetime.date(2009, 5, 4))
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, published__year=2009)

        years = Book.objects.using('other').dates('published', 'year')
        self.assertEqual([o.year for o in years], [2009])
        years = Book.objects.using('default').dates('published', 'year')
        self.assertEqual([o.year for o in years], [])

        months = Book.objects.using('other').dates('published', 'month')
        self.assertEqual([o.month for o in months], [5])
        months = Book.objects.using('default').dates('published', 'month')
        self.assertEqual([o.month for o in months], [])

    def test_m2m_separation(self):
        "M2M fields are constrained to a single database"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Save the author relations
        pro.authors = [marty]
        dive.authors = [mark]

        # Inspect the m2m tables directly.
        # There should be 1 entry in each database
        self.assertEquals(Book.authors.through.objects.using('default').count(), 1)
        self.assertEquals(Book.authors.through.objects.using('other').count(), 1)

        # Check that queries work across m2m joins
        self.assertEquals(list(Book.objects.using('default').filter(authors__name='Marty Alchin').values_list('title', flat=True)),
                          [u'Pro Django'])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Marty Alchin').values_list('title', flat=True)),
                          [])

        self.assertEquals(list(Book.objects.using('default').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [u'Dive into Python'])

        # Reget the objects to clear caches
        dive = Book.objects.using('other').get(title="Dive into Python")
        mark = Person.objects.using('other').get(name="Mark Pilgrim")

        # Retrive related object by descriptor. Related objects should be database-baound
        self.assertEquals(list(dive.authors.all().values_list('name', flat=True)),
                          [u'Mark Pilgrim'])

        self.assertEquals(list(mark.book_set.all().values_list('title', flat=True)),
                          [u'Dive into Python'])

    def test_m2m_forward_operations(self):
        "M2M forward manipulations are all constrained to a single DB"
        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Save the author relations
        dive.authors = [mark]

        # Add a second author
        john = Person.objects.using('other').create(name="John Smith")
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
                          [])


        dive.authors.add(john)
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [u'Dive into Python'])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
                          [u'Dive into Python'])

        # Remove the second author
        dive.authors.remove(john)
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [u'Dive into Python'])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
                          [])

        # Clear all authors
        dive.authors.clear()
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
                          [])

        # Create an author through the m2m interface
        dive.authors.create(name='Jane Brown')
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Jane Brown').values_list('title', flat=True)),
                          [u'Dive into Python'])

    def test_m2m_reverse_operations(self):
        "M2M reverse manipulations are all constrained to a single DB"
        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Save the author relations
        dive.authors = [mark]

        # Create a second book on the other database
        grease = Book.objects.using('other').create(title="Greasemonkey Hacks",
                                                    published=datetime.date(2005, 11, 1))

        # Add a books to the m2m
        mark.book_set.add(grease)
        self.assertEquals(list(Person.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
                          [u'Mark Pilgrim'])
        self.assertEquals(list(Person.objects.using('other').filter(book__title='Greasemonkey Hacks').values_list('name', flat=True)),
                          [u'Mark Pilgrim'])

        # Remove a book from the m2m
        mark.book_set.remove(grease)
        self.assertEquals(list(Person.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
                          [u'Mark Pilgrim'])
        self.assertEquals(list(Person.objects.using('other').filter(book__title='Greasemonkey Hacks').values_list('name', flat=True)),
                          [])

        # Clear the books associated with mark
        mark.book_set.clear()
        self.assertEquals(list(Person.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
                          [])
        self.assertEquals(list(Person.objects.using('other').filter(book__title='Greasemonkey Hacks').values_list('name', flat=True)),
                          [])

        # Create a book through the m2m interface
        mark.book_set.create(title="Dive into HTML5", published=datetime.date(2020, 1, 1))
        self.assertEquals(list(Person.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
                          [])
        self.assertEquals(list(Person.objects.using('other').filter(book__title='Dive into HTML5').values_list('name', flat=True)),
                          [u'Mark Pilgrim'])

    def test_m2m_cross_database_protection(self):
        "Operations that involve sharing M2M objects across databases raise an error"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")
        # Set a foreign key set with an object from a different database
        try:
            marty.book_set = [pro, dive]
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Add to an m2m with an object from a different database
        try:
            marty.book_set.add(dive)
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Set a m2m with an object from a different database
        try:
            marty.book_set = [pro, dive]
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Add to a reverse m2m with an object from a different database
        try:
            dive.authors.add(marty)
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Set a reverse m2m with an object from a different database
        try:
            dive.authors = [mark, marty]
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

    def test_foreign_key_separation(self):
        "FK fields are constrained to a single database"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")
        george = Person.objects.create(name="George Vilches")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")
        chris = Person.objects.using('other').create(name="Chris Mills")

        # Save the author's favourite books
        pro.editor = george
        pro.save()

        dive.editor = chris
        dive.save()

        pro = Book.objects.using('default').get(title="Pro Django")
        self.assertEquals(pro.editor.name, "George Vilches")

        dive = Book.objects.using('other').get(title="Dive into Python")
        self.assertEquals(dive.editor.name, "Chris Mills")

        # Check that queries work across foreign key joins
        self.assertEquals(list(Person.objects.using('default').filter(edited__title='Pro Django').values_list('name', flat=True)),
                          [u'George Vilches'])
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Pro Django').values_list('name', flat=True)),
                          [])

        self.assertEquals(list(Person.objects.using('default').filter(edited__title='Dive into Python').values_list('name', flat=True)),
                          [])
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into Python').values_list('name', flat=True)),
                          [u'Chris Mills'])

        # Reget the objects to clear caches
        chris = Person.objects.using('other').get(name="Chris Mills")
        dive = Book.objects.using('other').get(title="Dive into Python")

        # Retrive related object by descriptor. Related objects should be database-baound
        self.assertEquals(list(chris.edited.values_list('title', flat=True)),
                          [u'Dive into Python'])

    def test_foreign_key_reverse_operations(self):
        "FK reverse manipulations are all constrained to a single DB"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                       published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")
        chris = Person.objects.using('other').create(name="Chris Mills")

        # Save the author relations
        dive.editor = chris
        dive.save()

        # Add a second book edited by chris
        html5 = Book.objects.using('other').create(title="Dive into HTML5", published=datetime.date(2010, 3, 15))
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into HTML5').values_list('name', flat=True)),
                          [])

        chris.edited.add(html5)
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into HTML5').values_list('name', flat=True)),
                          [u'Chris Mills'])
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into Python').values_list('name', flat=True)),
                          [u'Chris Mills'])

        # Remove the second editor
        chris.edited.remove(html5)
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into HTML5').values_list('name', flat=True)),
                          [])
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into Python').values_list('name', flat=True)),
                          [u'Chris Mills'])

        # Clear all edited books
        chris.edited.clear()
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into HTML5').values_list('name', flat=True)),
                          [])
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into Python').values_list('name', flat=True)),
                          [])

        # Create an author through the m2m interface
        chris.edited.create(title='Dive into Water', published=datetime.date(2010, 3, 15))
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into HTML5').values_list('name', flat=True)),
                          [])
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into Water').values_list('name', flat=True)),
                          [u'Chris Mills'])
        self.assertEquals(list(Person.objects.using('other').filter(edited__title='Dive into Python').values_list('name', flat=True)),
                          [])

    def test_foreign_key_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Set a foreign key with an object from a different database
        try:
            dive.editor = marty
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Set a foreign key set with an object from a different database
        try:
            marty.edited = [pro, dive]
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Add to a foreign key set with an object from a different database
        try:
            marty.edited.add(dive)
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        chris = Person(name="Chris Mills")
        html5 = Book(title="Dive into HTML5", published=datetime.date(2010, 3, 15))
        # initially, no db assigned
        self.assertEquals(chris._state.db, None)
        self.assertEquals(html5._state.db, None)

        # old object comes from 'other', so the new object is set to use 'other'...
        dive.editor = chris
        html5.editor = mark
        self.assertEquals(chris._state.db, 'other')
        self.assertEquals(html5._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEquals(list(Person.objects.using('other').values_list('name',flat=True)),
                          [u'Mark Pilgrim'])
        self.assertEquals(list(Book.objects.using('other').values_list('title',flat=True)),
                           [u'Dive into Python'])

        # When saved (no using required), new objects goes to 'other'
        chris.save()
        html5.save()
        self.assertEquals(list(Person.objects.using('default').values_list('name',flat=True)),
                          [u'Marty Alchin'])
        self.assertEquals(list(Person.objects.using('other').values_list('name',flat=True)),
                          [u'Chris Mills', u'Mark Pilgrim'])
        self.assertEquals(list(Book.objects.using('default').values_list('title',flat=True)),
                          [u'Pro Django'])
        self.assertEquals(list(Book.objects.using('other').values_list('title',flat=True)),
                          [u'Dive into HTML5', u'Dive into Python'])

        # This also works if you assign the FK in the constructor
        water = Book(title="Dive into Water", published=datetime.date(2001, 1, 1), editor=mark)
        self.assertEquals(water._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEquals(list(Book.objects.using('default').values_list('title',flat=True)),
                          [u'Pro Django'])
        self.assertEquals(list(Book.objects.using('other').values_list('title',flat=True)),
                          [u'Dive into HTML5', u'Dive into Python'])

        # When saved, the new book goes to 'other'
        water.save()
        self.assertEquals(list(Book.objects.using('default').values_list('title',flat=True)),
                          [u'Pro Django'])
        self.assertEquals(list(Book.objects.using('other').values_list('title',flat=True)),
                          [u'Dive into HTML5', u'Dive into Python', u'Dive into Water'])

    def test_generic_key_separation(self):
        "Generic fields are constrained to a single database"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        review1 = Review.objects.create(source="Python Monthly", content_object=pro)

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        review2 = Review.objects.using('other').create(source="Python Weekly", content_object=dive)

        review1 = Review.objects.using('default').get(source="Python Monthly")
        self.assertEquals(review1.content_object.title, "Pro Django")

        review2 = Review.objects.using('other').get(source="Python Weekly")
        self.assertEquals(review2.content_object.title, "Dive into Python")

        # Reget the objects to clear caches
        dive = Book.objects.using('other').get(title="Dive into Python")

        # Retrive related object by descriptor. Related objects should be database-bound
        self.assertEquals(list(dive.reviews.all().values_list('source', flat=True)),
                          [u'Python Weekly'])

    def test_generic_key_reverse_operations(self):
        "Generic reverse manipulations are all constrained to a single DB"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        temp = Book.objects.using('other').create(title="Temp",
                                                  published=datetime.date(2009, 5, 4))

        review1 = Review.objects.using('other').create(source="Python Weekly", content_object=dive)
        review2 = Review.objects.using('other').create(source="Python Monthly", content_object=temp)

        self.assertEquals(list(Review.objects.using('default').filter(object_id=dive.pk).values_list('source', flat=True)),
                          [])
        self.assertEquals(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
                          [u'Python Weekly'])

        # Add a second review
        dive.reviews.add(review2)
        self.assertEquals(list(Review.objects.using('default').filter(object_id=dive.pk).values_list('source', flat=True)),
                          [])
        self.assertEquals(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
                          [u'Python Monthly', u'Python Weekly'])

        # Remove the second author
        dive.reviews.remove(review1)
        self.assertEquals(list(Review.objects.using('default').filter(object_id=dive.pk).values_list('source', flat=True)),
                          [])
        self.assertEquals(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
                          [u'Python Monthly'])

        # Clear all reviews
        dive.reviews.clear()
        self.assertEquals(list(Review.objects.using('default').filter(object_id=dive.pk).values_list('source', flat=True)),
                          [])
        self.assertEquals(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
                          [])

        # Create an author through the generic interface
        dive.reviews.create(source='Python Daily')
        self.assertEquals(list(Review.objects.using('default').filter(object_id=dive.pk).values_list('source', flat=True)),
                          [])
        self.assertEquals(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
                          [u'Python Daily'])

    def test_generic_key_cross_database_protection(self):
        "Operations that involve sharing generic key objects across databases raise an error"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        review1 = Review.objects.create(source="Python Monthly", content_object=pro)

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        review2 = Review.objects.using('other').create(source="Python Weekly", content_object=dive)

        # Set a foreign key with an object from a different database
        try:
            review1.content_object = dive
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Add to a foreign key set with an object from a different database
        try:
            dive.reviews.add(review1)
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        review3 = Review(source="Python Daily")
        # initially, no db assigned
        self.assertEquals(review3._state.db, None)

        # Dive comes from 'other', so review3 is set to use 'other'...
        review3.content_object = dive
        self.assertEquals(review3._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEquals(list(Review.objects.using('default').filter(object_id=pro.pk).values_list('source', flat=True)),
                          [u'Python Monthly'])
        self.assertEquals(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source',flat=True)),
                          [u'Python Weekly'])

        # When saved, John goes to 'other'
        review3.save()
        self.assertEquals(list(Review.objects.using('default').filter(object_id=pro.pk).values_list('source', flat=True)),
                          [u'Python Monthly'])
        self.assertEquals(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source',flat=True)),
                          [u'Python Daily', u'Python Weekly'])

    def test_ordering(self):
        "get_next_by_XXX commands stick to a single database"
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        learn = Book.objects.using('other').create(title="Learning Python",
                                                   published=datetime.date(2008, 7, 16))

        self.assertEquals(learn.get_next_by_published().title, "Dive into Python")
        self.assertEquals(dive.get_previous_by_published().title, "Learning Python")

    def test_raw(self):
        "test the raw() method across databases"
        dive = Book.objects.using('other').create(title="Dive into Python",
            published=datetime.date(2009, 5, 4))
        val = Book.objects.db_manager("other").raw('SELECT id FROM "multiple_database_book"')
        self.assertEqual(map(lambda o: o.pk, val), [dive.pk])

        val = Book.objects.raw('SELECT id FROM "multiple_database_book"').using('other')
        self.assertEqual(map(lambda o: o.pk, val), [dive.pk])

class TestRouter(object):
    # A test router. The behaviour is vaguely master/slave, but the
    # databases aren't assumed to propagate changes.
    def db_for_read(self, model, instance=None, **hints):
        if instance:
            return instance._state.db or 'other'
        return 'other'

    def db_for_write(self, model, **hints):
        return DEFAULT_DB_ALIAS

    def allow_relation(self, obj1, obj2, **hints):
        return obj1._state.db in ('default', 'other') and obj2._state.db in ('default', 'other')

    def allow_syncdb(self, db, model):
        return True

class AuthRouter(object):
    # Another test router. This one doesn't do anything interesting
    # other than validate syncdb behavior
    def db_for_read(self, model, **hints):
        return None
    def db_for_write(self, model, **hints):
        return None
    def allow_relation(self, obj1, obj2, **hints):
        return None
    def allow_syncdb(self, db, model):
        if db == 'other':
            return model._meta.app_label == 'auth'
        elif model._meta.app_label == 'auth':
            return False
        return None

class RouterTestCase(TestCase):
    multi_db = True

    def setUp(self):
        # Make the 'other' database appear to be a slave of the 'default'
        self.old_routers = router.routers
        router.routers = [TestRouter()]

    def tearDown(self):
        # Restore the 'other' database as an independent database
        router.routers = self.old_routers

    def test_db_selection(self):
        "Check that querysets obey the router for db suggestions"
        self.assertEquals(Book.objects.db, 'other')
        self.assertEquals(Book.objects.all().db, 'other')

        self.assertEquals(Book.objects.using('default').db, 'default')

        self.assertEquals(Book.objects.db_manager('default').db, 'default')
        self.assertEquals(Book.objects.db_manager('default').all().db, 'default')

    def test_syncdb_selection(self):
        "Synchronization behaviour is predicatable"

        self.assertTrue(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        self.assertTrue(router.allow_syncdb('other', User))
        self.assertTrue(router.allow_syncdb('other', Book))

        # Add the auth router to the chain.
        # TestRouter is a universal synchronizer, so it should have no effect.
        router.routers = [TestRouter(), AuthRouter()]

        self.assertTrue(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        self.assertTrue(router.allow_syncdb('other', User))
        self.assertTrue(router.allow_syncdb('other', Book))

        # Now check what happens if the router order is the other way around
        router.routers = [AuthRouter(), TestRouter()]

        self.assertFalse(router.allow_syncdb('default', User))
        self.assertTrue(router.allow_syncdb('default', Book))

        self.assertTrue(router.allow_syncdb('other', User))
        self.assertFalse(router.allow_syncdb('other', Book))


    def test_database_routing(self):
        marty = Person.objects.using('default').create(name="Marty Alchin")
        pro = Book.objects.using('default').create(title="Pro Django",
                                                   published=datetime.date(2008, 12, 16),
                                                   editor=marty)
        pro.authors = [marty]

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        # An update query will be routed to the default database
        Book.objects.filter(title='Pro Django').update(pages=200)

        try:
            # By default, the get query will be directed to 'other'
            Book.objects.get(title='Pro Django')
            self.fail("Shouldn't be able to find the book")
        except Book.DoesNotExist:
            pass

        # But the same query issued explicitly at a database will work.
        pro = Book.objects.using('default').get(title='Pro Django')

        # Check that the update worked.
        self.assertEquals(pro.pages, 200)

        # An update query with an explicit using clause will be routed
        # to the requested database.
        Book.objects.using('other').filter(title='Dive into Python').update(pages=300)
        self.assertEquals(Book.objects.get(title='Dive into Python').pages, 300)

        # Related object queries stick to the same database
        # as the original object, regardless of the router
        self.assertEquals(list(pro.authors.values_list('name', flat=True)), [u'Marty Alchin'])
        self.assertEquals(pro.editor.name, u'Marty Alchin')

        # get_or_create is a special case. The get needs to be targetted at
        # the write database in order to avoid potential transaction
        # consistency problems
        book, created = Book.objects.get_or_create(title="Pro Django")
        self.assertFalse(created)

        book, created = Book.objects.get_or_create(title="Dive Into Python",
                                                   defaults={'published':datetime.date(2009, 5, 4)})
        self.assertTrue(created)

        # Check the head count of objects
        self.assertEquals(Book.objects.using('default').count(), 2)
        self.assertEquals(Book.objects.using('other').count(), 1)
        # If a database isn't specified, the read database is used
        self.assertEquals(Book.objects.count(), 1)

        # A delete query will also be routed to the default database
        Book.objects.filter(pages__gt=150).delete()

        # The default database has lost the book.
        self.assertEquals(Book.objects.using('default').count(), 1)
        self.assertEquals(Book.objects.using('other').count(), 1)

    def test_foreign_key_cross_database_protection(self):
        "Foreign keys can cross databases if they two databases have a common source"
        # Create a book and author on the default database
        pro = Book.objects.using('default').create(title="Pro Django",
                                                   published=datetime.date(2008, 12, 16))

        marty = Person.objects.using('default').create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Set a foreign key with an object from a different database
        try:
            dive.editor = marty
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEquals(marty._state.db, 'default')
        self.assertEquals(pro._state.db, 'default')
        self.assertEquals(dive._state.db, 'other')
        self.assertEquals(mark._state.db, 'other')

        # ... but they will when the affected object is saved.
        dive.save()
        self.assertEquals(dive._state.db, 'default')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real master-slave database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')
        self.assertEquals(dive._state.db, 'other')

        # Set a foreign key set with an object from a different database
        try:
            marty.edited = [pro, dive]
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Assignment implies a save, so database assignments of original objects have changed...
        self.assertEquals(marty._state.db, 'default')
        self.assertEquals(pro._state.db, 'default')
        self.assertEquals(dive._state.db, 'default')
        self.assertEquals(mark._state.db, 'other')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real master-slave database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')
        self.assertEquals(dive._state.db, 'other')

        # Add to a foreign key set with an object from a different database
        try:
            marty.edited.add(dive)
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Add implies a save, so database assignments of original objects have changed...
        self.assertEquals(marty._state.db, 'default')
        self.assertEquals(pro._state.db, 'default')
        self.assertEquals(dive._state.db, 'default')
        self.assertEquals(mark._state.db, 'other')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real master-slave database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')

        # If you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        chris = Person(name="Chris Mills")
        html5 = Book(title="Dive into HTML5", published=datetime.date(2010, 3, 15))
        # initially, no db assigned
        self.assertEquals(chris._state.db, None)
        self.assertEquals(html5._state.db, None)

        # old object comes from 'other', so the new object is set to use the
        # source of 'other'...
        self.assertEquals(dive._state.db, 'other')
        dive.editor = chris
        html5.editor = mark

        self.assertEquals(dive._state.db, 'other')
        self.assertEquals(mark._state.db, 'other')
        self.assertEquals(chris._state.db, 'default')
        self.assertEquals(html5._state.db, 'default')

        # This also works if you assign the FK in the constructor
        water = Book(title="Dive into Water", published=datetime.date(2001, 1, 1), editor=mark)
        self.assertEquals(water._state.db, 'default')

    def test_m2m_cross_database_protection(self):
        "M2M relations can cross databases if the database share a source"
        # Create books and authors on the inverse to the usual database
        pro = Book.objects.using('other').create(pk=1, title="Pro Django",
                                                 published=datetime.date(2008, 12, 16))

        marty = Person.objects.using('other').create(pk=1, name="Marty Alchin")

        dive = Book.objects.using('default').create(pk=2, title="Dive into Python",
                                                    published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('default').create(pk=2, name="Mark Pilgrim")

        # Now save back onto the usual databse.
        # This simulates master/slave - the objects exist on both database,
        # but the _state.db is as it is for all other tests.
        pro.save(using='default')
        marty.save(using='default')
        dive.save(using='other')
        mark.save(using='other')

        # Check that we have 2 of both types of object on both databases
        self.assertEquals(Book.objects.using('default').count(), 2)
        self.assertEquals(Book.objects.using('other').count(), 2)
        self.assertEquals(Person.objects.using('default').count(), 2)
        self.assertEquals(Person.objects.using('other').count(), 2)

        # Set a m2m set with an object from a different database
        try:
            marty.book_set = [pro, dive]
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments don't change
        self.assertEquals(marty._state.db, 'default')
        self.assertEquals(pro._state.db, 'default')
        self.assertEquals(dive._state.db, 'other')
        self.assertEquals(mark._state.db, 'other')

        # All m2m relations should be saved on the default database
        self.assertEquals(Book.authors.through.objects.using('default').count(), 2)
        self.assertEquals(Book.authors.through.objects.using('other').count(), 0)

        # Reset relations
        Book.authors.through.objects.using('default').delete()

        # Add to an m2m with an object from a different database
        try:
            marty.book_set.add(dive)
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments don't change
        self.assertEquals(marty._state.db, 'default')
        self.assertEquals(pro._state.db, 'default')
        self.assertEquals(dive._state.db, 'other')
        self.assertEquals(mark._state.db, 'other')

        # All m2m relations should be saved on the default database
        self.assertEquals(Book.authors.through.objects.using('default').count(), 1)
        self.assertEquals(Book.authors.through.objects.using('other').count(), 0)

        # Reset relations
        Book.authors.through.objects.using('default').delete()

        # Set a reverse m2m with an object from a different database
        try:
            dive.authors = [mark, marty]
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments don't change
        self.assertEquals(marty._state.db, 'default')
        self.assertEquals(pro._state.db, 'default')
        self.assertEquals(dive._state.db, 'other')
        self.assertEquals(mark._state.db, 'other')

        # All m2m relations should be saved on the default database
        self.assertEquals(Book.authors.through.objects.using('default').count(), 2)
        self.assertEquals(Book.authors.through.objects.using('other').count(), 0)

        # Reset relations
        Book.authors.through.objects.using('default').delete()

        self.assertEquals(Book.authors.through.objects.using('default').count(), 0)
        self.assertEquals(Book.authors.through.objects.using('other').count(), 0)

        # Add to a reverse m2m with an object from a different database
        try:
            dive.authors.add(marty)
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments don't change
        self.assertEquals(marty._state.db, 'default')
        self.assertEquals(pro._state.db, 'default')
        self.assertEquals(dive._state.db, 'other')
        self.assertEquals(mark._state.db, 'other')

        # All m2m relations should be saved on the default database
        self.assertEquals(Book.authors.through.objects.using('default').count(), 1)
        self.assertEquals(Book.authors.through.objects.using('other').count(), 0)

    def test_generic_key_cross_database_protection(self):
        "Generic Key operations can span databases if they share a source"
        # Create a book and author on the default database
        pro = Book.objects.using('default'
                ).create(title="Pro Django", published=datetime.date(2008, 12, 16))

        review1 = Review.objects.using('default'
                    ).create(source="Python Monthly", content_object=pro)

        # Create a book and author on the other database
        dive = Book.objects.using('other'
                ).create(title="Dive into Python", published=datetime.date(2009, 5, 4))

        review2 = Review.objects.using('other'
                    ).create(source="Python Weekly", content_object=dive)

        # Set a generic foreign key with an object from a different database
        try:
            review1.content_object = dive
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEquals(pro._state.db, 'default')
        self.assertEquals(review1._state.db, 'default')
        self.assertEquals(dive._state.db, 'other')
        self.assertEquals(review2._state.db, 'other')

        # ... but they will when the affected object is saved.
        dive.save()
        self.assertEquals(review1._state.db, 'default')
        self.assertEquals(dive._state.db, 'default')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real master-slave database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')
        self.assertEquals(dive._state.db, 'other')

        # Add to a generic foreign key set with an object from a different database
        try:
            dive.reviews.add(review1)
        except ValueError:
            self.fail("Assignment across master/slave databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEquals(pro._state.db, 'default')
        self.assertEquals(review1._state.db, 'default')
        self.assertEquals(dive._state.db, 'other')
        self.assertEquals(review2._state.db, 'other')

        # ... but they will when the affected object is saved.
        dive.save()
        self.assertEquals(dive._state.db, 'default')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        review3 = Review(source="Python Daily")
        # initially, no db assigned
        self.assertEquals(review3._state.db, None)

        # Dive comes from 'other', so review3 is set to use the source of 'other'...
        review3.content_object = dive
        self.assertEquals(review3._state.db, 'default')


class UserProfileTestCase(TestCase):
    def setUp(self):
        self.old_auth_profile_module = getattr(settings, 'AUTH_PROFILE_MODULE', None)
        settings.AUTH_PROFILE_MODULE = 'multiple_database.UserProfile'

    def tearDown(self):
        settings.AUTH_PROFILE_MODULE = self.old_auth_profile_module

    def test_user_profiles(self):

        alice = User.objects.create_user('alice', 'alice@example.com')
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')

        alice_profile = UserProfile(user=alice, flavor='chocolate')
        alice_profile.save()

        bob_profile = UserProfile(user=bob, flavor='crunchy frog')
        bob_profile.save()

        self.assertEquals(alice.get_profile().flavor, 'chocolate')
        self.assertEquals(bob.get_profile().flavor, 'crunchy frog')


class FixtureTestCase(TestCase):
    multi_db = True
    fixtures = ['multidb-common', 'multidb']

    def test_fixture_loading(self):
        "Multi-db fixtures are loaded correctly"
        # Check that "Pro Django" exists on the default database, but not on other database
        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Pro Django" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )

        # Check that "Dive into Python" exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Dive into Python"
        )

        # Check that "Definitive Guide" exists on the both databases
        try:
            Book.objects.get(title="The Definitive Guide to Django")
            Book.objects.using('default').get(title="The Definitive Guide to Django")
            Book.objects.using('other').get(title="The Definitive Guide to Django")
        except Book.DoesNotExist:
            self.fail('"The Definitive Guide to Django" should exist on both databases')


class PickleQuerySetTestCase(TestCase):
    multi_db = True

    def test_pickling(self):
        for db in connections:
            Book.objects.using(db).create(title='Dive into Python', published=datetime.date(2009, 5, 4))
            qs = Book.objects.all()
            self.assertEqual(qs.db, pickle.loads(pickle.dumps(qs)).db)
