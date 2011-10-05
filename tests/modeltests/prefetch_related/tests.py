from __future__ import with_statement

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import unittest

from models import (Author, Book, Reader, Qualification, Teacher, Department,
                    TaggedItem, Bookmark, AuthorAddress, FavoriteAuthors,
                    AuthorWithAge, BookWithYear, Person, House, Room,
                    Employee)


class PrefetchRelatedTests(TestCase):

    def setUp(self):

        self.book1 = Book.objects.create(title="Poems")
        self.book2 = Book.objects.create(title="Jane Eyre")
        self.book3 = Book.objects.create(title="Wuthering Heights")
        self.book4 = Book.objects.create(title="Sense and Sensibility")

        self.author1 = Author.objects.create(name="Charlotte",
                                             first_book=self.book1)
        self.author2 = Author.objects.create(name="Anne",
                                             first_book=self.book1)
        self.author3 = Author.objects.create(name="Emily",
                                             first_book=self.book1)
        self.author4 = Author.objects.create(name="Jane",
                                             first_book=self.book4)

        self.book1.authors.add(self.author1, self.author2, self.author3)
        self.book2.authors.add(self.author1)
        self.book3.authors.add(self.author3)
        self.book4.authors.add(self.author4)

        self.reader1 = Reader.objects.create(name="Amy")
        self.reader2 = Reader.objects.create(name="Belinda")

        self.reader1.books_read.add(self.book1, self.book4)
        self.reader2.books_read.add(self.book2, self.book4)

    def test_m2m_forward(self):
        with self.assertNumQueries(2):
            lists = [list(b.authors.all()) for b in Book.objects.prefetch_related('authors')]

        normal_lists = [list(b.authors.all()) for b in Book.objects.all()]
        self.assertEqual(lists, normal_lists)


    def test_m2m_reverse(self):
        with self.assertNumQueries(2):
            lists = [list(a.books.all()) for a in Author.objects.prefetch_related('books')]

        normal_lists = [list(a.books.all()) for a in Author.objects.all()]
        self.assertEqual(lists, normal_lists)

    def test_foreignkey_reverse(self):
        with self.assertNumQueries(2):
            lists = [list(b.first_time_authors.all())
                     for b in Book.objects.prefetch_related('first_time_authors')]

        self.assertQuerysetEqual(self.book2.authors.all(), [u"<Author: Charlotte>"])

    def test_survives_clone(self):
        with self.assertNumQueries(2):
            lists = [list(b.first_time_authors.all())
                     for b in Book.objects.prefetch_related('first_time_authors').exclude(id=1000)]

    def test_len(self):
        with self.assertNumQueries(2):
            qs = Book.objects.prefetch_related('first_time_authors')
            length = len(qs)
            lists = [list(b.first_time_authors.all())
                     for b in qs]

    def test_bool(self):
        with self.assertNumQueries(2):
            qs = Book.objects.prefetch_related('first_time_authors')
            x = bool(qs)
            lists = [list(b.first_time_authors.all())
                     for b in qs]

    def test_count(self):
        with self.assertNumQueries(2):
            qs = Book.objects.prefetch_related('first_time_authors')
            [b.first_time_authors.count() for b in qs]

    def test_exists(self):
        with self.assertNumQueries(2):
            qs = Book.objects.prefetch_related('first_time_authors')
            [b.first_time_authors.exists() for b in qs]

    def test_clear(self):
        """
        Test that we can clear the behavior by calling prefetch_related()
        """
        with self.assertNumQueries(5):
            with_prefetch = Author.objects.prefetch_related('books')
            without_prefetch = with_prefetch.prefetch_related(None)
            lists = [list(a.books.all()) for a in without_prefetch]

    def test_m2m_then_m2m(self):
        """
        Test we can follow a m2m and another m2m
        """
        with self.assertNumQueries(3):
            qs = Author.objects.prefetch_related('books__read_by')
            lists = [[[unicode(r) for r in b.read_by.all()]
                      for b in a.books.all()]
                     for a in qs]
            self.assertEqual(lists,
            [
                [[u"Amy"], [u"Belinda"]],  # Charlotte - Poems, Jane Eyre
                [[u"Amy"]],                # Anne - Poems
                [[u"Amy"], []],            # Emily - Poems, Wuthering Heights
                [[u"Amy", u"Belinda"]],    # Jane - Sense and Sense
            ])

    def test_overriding_prefetch(self):
        with self.assertNumQueries(3):
            qs = Author.objects.prefetch_related('books', 'books__read_by')
            lists = [[[unicode(r) for r in b.read_by.all()]
                      for b in a.books.all()]
                     for a in qs]
            self.assertEqual(lists,
            [
                [[u"Amy"], [u"Belinda"]],  # Charlotte - Poems, Jane Eyre
                [[u"Amy"]],                # Anne - Poems
                [[u"Amy"], []],            # Emily - Poems, Wuthering Heights
                [[u"Amy", u"Belinda"]],    # Jane - Sense and Sense
            ])
        with self.assertNumQueries(3):
            qs = Author.objects.prefetch_related('books__read_by', 'books')
            lists = [[[unicode(r) for r in b.read_by.all()]
                      for b in a.books.all()]
                     for a in qs]
            self.assertEqual(lists,
            [
                [[u"Amy"], [u"Belinda"]],  # Charlotte - Poems, Jane Eyre
                [[u"Amy"]],                # Anne - Poems
                [[u"Amy"], []],            # Emily - Poems, Wuthering Heights
                [[u"Amy", u"Belinda"]],    # Jane - Sense and Sense
            ])

    def test_get(self):
        """
        Test that objects retrieved with .get() get the prefetch behaviour
        """
        # Need a double
        with self.assertNumQueries(3):
            author = Author.objects.prefetch_related('books__read_by').get(name="Charlotte")
            lists = [[unicode(r) for r in b.read_by.all()]
                      for b in author.books.all()]
            self.assertEqual(lists, [[u"Amy"], [u"Belinda"]])  # Poems, Jane Eyre

    def test_foreign_key_then_m2m(self):
        """
        Test we can follow an m2m relation after a relation like ForeignKey
        that doesn't have many objects
        """
        with self.assertNumQueries(2):
            qs = Author.objects.select_related('first_book').prefetch_related('first_book__read_by')
            lists = [[unicode(r) for r in a.first_book.read_by.all()]
                     for a in qs]
            self.assertEqual(lists, [[u"Amy"],
                                     [u"Amy"],
                                     [u"Amy"],
                                     [u"Amy", "Belinda"]])

    def test_attribute_error(self):
        qs = Reader.objects.all().prefetch_related('books_read__xyz')
        with self.assertRaises(AttributeError) as cm:
            list(qs)

        self.assertTrue('prefetch_related' in str(cm.exception))

    def test_invalid_final_lookup(self):
        qs = Book.objects.prefetch_related('authors__first_book')
        with self.assertRaises(ValueError) as cm:
            list(qs)

        self.assertTrue('prefetch_related' in str(cm.exception))
        self.assertTrue("first_book" in str(cm.exception))


class DefaultManagerTests(TestCase):

    def setUp(self):
        self.qual1 = Qualification.objects.create(name="BA")
        self.qual2 = Qualification.objects.create(name="BSci")
        self.qual3 = Qualification.objects.create(name="MA")
        self.qual4 = Qualification.objects.create(name="PhD")

        self.teacher1 = Teacher.objects.create(name="Mr Cleese")
        self.teacher2 = Teacher.objects.create(name="Mr Idle")
        self.teacher3 = Teacher.objects.create(name="Mr Chapman")

        self.teacher1.qualifications.add(self.qual1, self.qual2, self.qual3, self.qual4)
        self.teacher2.qualifications.add(self.qual1)
        self.teacher3.qualifications.add(self.qual2)

        self.dept1 = Department.objects.create(name="English")
        self.dept2 = Department.objects.create(name="Physics")

        self.dept1.teachers.add(self.teacher1, self.teacher2)
        self.dept2.teachers.add(self.teacher1, self.teacher3)

    def test_m2m_then_m2m(self):
        with self.assertNumQueries(3):
            # When we prefetch the teachers, and force the query, we don't want
            # the default manager on teachers to immediately get all the related
            # qualifications, since this will do one query per teacher.
            qs = Department.objects.prefetch_related('teachers')
            depts = "".join(["%s department: %s\n" %
                             (dept.name, ", ".join(unicode(t) for t in dept.teachers.all()))
                             for dept in qs])

            self.assertEqual(depts,
                             "English department: Mr Cleese (BA, BSci, MA, PhD), Mr Idle (BA)\n"
                             "Physics department: Mr Cleese (BA, BSci, MA, PhD), Mr Chapman (BSci)\n")


class GenericRelationTests(TestCase):

    def test_traverse_GFK(self):
        """
        Test that we can traverse a 'content_object' with prefetch_related()
        """
        # In fact, there is no special support for this in prefetch_related code
        # - we can traverse any object that will lead us to objects that have
        # related managers.

        book1 = Book.objects.create(title="Winnie the Pooh")
        book2 = Book.objects.create(title="Do you like green eggs and spam?")

        reader1 = Reader.objects.create(name="me")
        reader2 = Reader.objects.create(name="you")

        book1.read_by.add(reader1)
        book2.read_by.add(reader2)

        TaggedItem.objects.create(tag="awesome", content_object=book1)
        TaggedItem.objects.create(tag="awesome", content_object=book2)

        ct = ContentType.objects.get_for_model(Book)

        # We get 4 queries - 1 for main query, 2 for each access to
        # 'content_object' because these can't be handled by select_related, and
        # 1 for the 'read_by' relation.
        with self.assertNumQueries(4):
            # If we limit to books, we know that they will have 'read_by'
            # attributes, so the following makes sense:
            qs = TaggedItem.objects.select_related('content_type').prefetch_related('content_object__read_by').filter(tag='awesome').filter(content_type=ct, tag='awesome')
            readers_of_awesome_books = [r.name for tag in qs
                                        for r in tag.content_object.read_by.all()]
            self.assertEqual(readers_of_awesome_books, ["me", "you"])


    def test_generic_relation(self):
        b = Bookmark.objects.create(url='http://www.djangoproject.com/')
        t1 = TaggedItem.objects.create(content_object=b, tag='django')
        t2 = TaggedItem.objects.create(content_object=b, tag='python')

        with self.assertNumQueries(2):
            tags = [t.tag for b in Bookmark.objects.prefetch_related('tags')
                    for t in b.tags.all()]
            self.assertEqual(sorted(tags), ["django", "python"])


class MultiTableInheritanceTest(TestCase):

    def setUp(self):
        self.book1 = BookWithYear.objects.create(
            title="Poems", published_year=2010)
        self.book2 = BookWithYear.objects.create(
            title="More poems", published_year=2011)
        self.author1 = AuthorWithAge.objects.create(
            name='Jane', first_book=self.book1, age=50)
        self.author2 = AuthorWithAge.objects.create(
            name='Tom', first_book=self.book1, age=49)
        self.author3 = AuthorWithAge.objects.create(
            name='Robert', first_book=self.book2, age=48)
        self.authorAddress = AuthorAddress.objects.create(
            author=self.author1, address='SomeStreet 1')
        self.book2.aged_authors.add(self.author2, self.author3)

    def test_foreignkey(self):
        with self.assertNumQueries(2):
            qs = AuthorWithAge.objects.prefetch_related('addresses')
            addresses = [[unicode(address) for address in obj.addresses.all()]
                         for obj in qs]
        self.assertEquals(addresses, [[unicode(self.authorAddress)], [], []])

    def test_m2m_to_inheriting_model(self):
        qs = AuthorWithAge.objects.prefetch_related('books_with_year')
        with self.assertNumQueries(2):
            lst = [[unicode(book) for book in author.books_with_year.all()]
                   for author in qs]
        qs = AuthorWithAge.objects.all()
        lst2 = [[unicode(book) for book in author.books_with_year.all()]
                for author in qs]
        self.assertEquals(lst, lst2)

        qs = BookWithYear.objects.prefetch_related('aged_authors')
        with self.assertNumQueries(2):
            lst = [[unicode(author) for author in book.aged_authors.all()]
                   for book in qs]
        qs = BookWithYear.objects.all()
        lst2 = [[unicode(author) for author in book.aged_authors.all()]
               for book in qs]
        self.assertEquals(lst, lst2)

    def test_parent_link_prefetch(self):
        with self.assertRaises(ValueError) as cm:
            qs = list(AuthorWithAge.objects.prefetch_related('author'))
        self.assertTrue('prefetch_related' in str(cm.exception))


class ForeignKeyToFieldTest(TestCase):

    def setUp(self):
        self.book = Book.objects.create(title="Poems")
        self.author1 = Author.objects.create(name='Jane', first_book=self.book)
        self.author2 = Author.objects.create(name='Tom', first_book=self.book)
        self.author3 = Author.objects.create(name='Robert', first_book=self.book)
        self.authorAddress = AuthorAddress.objects.create(
            author=self.author1, address='SomeStreet 1'
        )
        FavoriteAuthors.objects.create(author=self.author1,
                                       likes_author=self.author2)
        FavoriteAuthors.objects.create(author=self.author2,
                                       likes_author=self.author3)
        FavoriteAuthors.objects.create(author=self.author3,
                                       likes_author=self.author1)

    def test_foreignkey(self):
        with self.assertNumQueries(2):
            qs = Author.objects.prefetch_related('addresses')
            addresses = [[unicode(address) for address in obj.addresses.all()]
                         for obj in qs]
        self.assertEquals(addresses, [[unicode(self.authorAddress)], [], []])

    def test_m2m(self):
        with self.assertNumQueries(3):
            qs = Author.objects.all().prefetch_related('favorite_authors', 'favors_me')
            favorites = [(
                 [unicode(i_like) for i_like in author.favorite_authors.all()],
                 [unicode(likes_me) for likes_me in author.favors_me.all()]
                ) for author in qs]
            self.assertEquals(
                favorites,
                [
                    ([unicode(self.author2)],[unicode(self.author3)]),
                    ([unicode(self.author3)],[unicode(self.author1)]),
                    ([unicode(self.author1)],[unicode(self.author2)])
                ]
            )


class LookupOrderingTest(TestCase):
    """
    Test cases that demonstrate that ordering of lookups is important, and
    ensure it is preserved.
    """

    def setUp(self):
        self.person1 = Person.objects.create(name="Joe")
        self.person2 = Person.objects.create(name="Mary")

        self.house1 = House.objects.create(address="123 Main St")
        self.house2 = House.objects.create(address="45 Side St")
        self.house3 = House.objects.create(address="6 Downing St")
        self.house4 = House.objects.create(address="7 Regents St")

        self.room1_1 = Room.objects.create(name="Dining room", house=self.house1)
        self.room1_2 = Room.objects.create(name="Lounge", house=self.house1)
        self.room1_3 = Room.objects.create(name="Kitchen", house=self.house1)

        self.room2_1 = Room.objects.create(name="Dining room", house=self.house2)
        self.room2_2 = Room.objects.create(name="Lounge", house=self.house2)

        self.room3_1 = Room.objects.create(name="Dining room", house=self.house3)
        self.room3_2 = Room.objects.create(name="Lounge", house=self.house3)
        self.room3_3 = Room.objects.create(name="Kitchen", house=self.house3)

        self.room4_1 = Room.objects.create(name="Dining room", house=self.house4)
        self.room4_2 = Room.objects.create(name="Lounge", house=self.house4)

        self.person1.houses.add(self.house1, self.house2)
        self.person2.houses.add(self.house3, self.house4)

    def test_order(self):
        with self.assertNumQueries(4):
            # The following two queries must be done in the same order as written,
            # otherwise 'primary_house' will cause non-prefetched lookups
            qs = Person.objects.prefetch_related('houses__rooms',
                                                 'primary_house__occupants')
            [list(p.primary_house.occupants.all()) for p in qs]


class NullableTest(TestCase):

    def setUp(self):
        boss = Employee.objects.create(name="Peter")
        worker1 = Employee.objects.create(name="Joe", boss=boss)
        worker2 = Employee.objects.create(name="Angela", boss=boss)

    def test_traverse_nullable(self):
        with self.assertNumQueries(2):
            qs = Employee.objects.select_related('boss').prefetch_related('boss__serfs')
            co_serfs = [list(e.boss.serfs.all()) if e.boss is not None else []
                        for e in qs]

        qs2 =  Employee.objects.select_related('boss')
        co_serfs2 =  [list(e.boss.serfs.all()) if e.boss is not None else []
                        for e in qs2]

        self.assertEqual(co_serfs, co_serfs2)
