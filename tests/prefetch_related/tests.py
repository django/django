from __future__ import absolute_import, unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models.query import get_prefetcher
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import six
from django.utils.encoding import force_text

from .models import (Author, Book, Reader, Qualification, Teacher, Department,
    TaggedItem, Bookmark, AuthorAddress, FavoriteAuthors, AuthorWithAge,
    BookWithYear, BookReview, Person, House, Room, Employee, Comment,
    LessonEntry, WordEntry, Author2)


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

    def test_foreignkey_forward(self):
        with self.assertNumQueries(2):
            books = [a.first_book for a in Author.objects.prefetch_related('first_book')]

        normal_books = [a.first_book for a in Author.objects.all()]
        self.assertEqual(books, normal_books)

    def test_foreignkey_reverse(self):
        with self.assertNumQueries(2):
            lists = [list(b.first_time_authors.all())
                     for b in Book.objects.prefetch_related('first_time_authors')]

        self.assertQuerysetEqual(self.book2.authors.all(), ["<Author: Charlotte>"])

    def test_onetoone_reverse_no_match(self):
        # Regression for #17439
        with self.assertNumQueries(2):
            book = Book.objects.prefetch_related('bookwithyear').all()[0]
        with self.assertNumQueries(0):
            with self.assertRaises(BookWithYear.DoesNotExist):
                book.bookwithyear

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

    def test_in_and_prefetch_related(self):
        """
        Regression test for #20242 - QuerySet "in" didn't work the first time
        when using prefetch_related. This was fixed by the removal of chunked
        reads from QuerySet iteration in
        70679243d1786e03557c28929f9762a119e3ac14.
        """
        qs = Book.objects.prefetch_related('first_time_authors')
        self.assertTrue(qs[0] in qs)

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
            lists = [[[six.text_type(r) for r in b.read_by.all()]
                      for b in a.books.all()]
                     for a in qs]
            self.assertEqual(lists,
            [
                [["Amy"], ["Belinda"]],  # Charlotte - Poems, Jane Eyre
                [["Amy"]],                # Anne - Poems
                [["Amy"], []],            # Emily - Poems, Wuthering Heights
                [["Amy", "Belinda"]],    # Jane - Sense and Sense
            ])

    def test_overriding_prefetch(self):
        with self.assertNumQueries(3):
            qs = Author.objects.prefetch_related('books', 'books__read_by')
            lists = [[[six.text_type(r) for r in b.read_by.all()]
                      for b in a.books.all()]
                     for a in qs]
            self.assertEqual(lists,
            [
                [["Amy"], ["Belinda"]],  # Charlotte - Poems, Jane Eyre
                [["Amy"]],                # Anne - Poems
                [["Amy"], []],            # Emily - Poems, Wuthering Heights
                [["Amy", "Belinda"]],    # Jane - Sense and Sense
            ])
        with self.assertNumQueries(3):
            qs = Author.objects.prefetch_related('books__read_by', 'books')
            lists = [[[six.text_type(r) for r in b.read_by.all()]
                      for b in a.books.all()]
                     for a in qs]
            self.assertEqual(lists,
            [
                [["Amy"], ["Belinda"]],  # Charlotte - Poems, Jane Eyre
                [["Amy"]],                # Anne - Poems
                [["Amy"], []],            # Emily - Poems, Wuthering Heights
                [["Amy", "Belinda"]],    # Jane - Sense and Sense
            ])

    def test_get(self):
        """
        Test that objects retrieved with .get() get the prefetch behavior.
        """
        # Need a double
        with self.assertNumQueries(3):
            author = Author.objects.prefetch_related('books__read_by').get(name="Charlotte")
            lists = [[six.text_type(r) for r in b.read_by.all()]
                      for b in author.books.all()]
            self.assertEqual(lists, [["Amy"], ["Belinda"]])  # Poems, Jane Eyre

    def test_foreign_key_then_m2m(self):
        """
        Test we can follow an m2m relation after a relation like ForeignKey
        that doesn't have many objects
        """
        with self.assertNumQueries(2):
            qs = Author.objects.select_related('first_book').prefetch_related('first_book__read_by')
            lists = [[six.text_type(r) for r in a.first_book.read_by.all()]
                     for a in qs]
            self.assertEqual(lists, [["Amy"],
                                     ["Amy"],
                                     ["Amy"],
                                     ["Amy", "Belinda"]])

    def test_attribute_error(self):
        qs = Reader.objects.all().prefetch_related('books_read__xyz')
        with self.assertRaises(AttributeError) as cm:
            list(qs)

        self.assertTrue('prefetch_related' in str(cm.exception))

    def test_invalid_final_lookup(self):
        qs = Book.objects.prefetch_related('authors__name')
        with self.assertRaises(ValueError) as cm:
            list(qs)

        self.assertTrue('prefetch_related' in str(cm.exception))
        self.assertTrue("name" in str(cm.exception))


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
                             (dept.name, ", ".join(six.text_type(t) for t in dept.teachers.all()))
                             for dept in qs])

            self.assertEqual(depts,
                             "English department: Mr Cleese (BA, BSci, MA, PhD), Mr Idle (BA)\n"
                             "Physics department: Mr Cleese (BA, BSci, MA, PhD), Mr Chapman (BSci)\n")


class GenericRelationTests(TestCase):

    def setUp(self):
        book1 = Book.objects.create(title="Winnie the Pooh")
        book2 = Book.objects.create(title="Do you like green eggs and spam?")
        book3 = Book.objects.create(title="Three Men In A Boat")

        reader1 = Reader.objects.create(name="me")
        reader2 = Reader.objects.create(name="you")
        reader3 = Reader.objects.create(name="someone")

        book1.read_by.add(reader1, reader2)
        book2.read_by.add(reader2)
        book3.read_by.add(reader3)

        self.book1, self.book2, self.book3 = book1, book2, book3
        self.reader1, self.reader2, self.reader3 = reader1, reader2, reader3

    def test_prefetch_GFK(self):
        TaggedItem.objects.create(tag="awesome", content_object=self.book1)
        TaggedItem.objects.create(tag="great", content_object=self.reader1)
        TaggedItem.objects.create(tag="stupid", content_object=self.book2)
        TaggedItem.objects.create(tag="amazing", content_object=self.reader3)

        # 1 for TaggedItem table, 1 for Book table, 1 for Reader table
        with self.assertNumQueries(3):
            qs = TaggedItem.objects.prefetch_related('content_object')
            list(qs)

    def test_prefetch_GFK_nonint_pk(self):
        Comment.objects.create(comment="awesome", content_object=self.book1)

        # 1 for Comment table, 1 for Book table
        with self.assertNumQueries(2):
            qs = Comment.objects.prefetch_related('content_object')
            [c.content_object for c in qs]

    def test_traverse_GFK(self):
        """
        Test that we can traverse a 'content_object' with prefetch_related() and
        get to related objects on the other side (assuming it is suitably
        filtered)
        """
        TaggedItem.objects.create(tag="awesome", content_object=self.book1)
        TaggedItem.objects.create(tag="awesome", content_object=self.book2)
        TaggedItem.objects.create(tag="awesome", content_object=self.book3)
        TaggedItem.objects.create(tag="awesome", content_object=self.reader1)
        TaggedItem.objects.create(tag="awesome", content_object=self.reader2)

        ct = ContentType.objects.get_for_model(Book)

        # We get 3 queries - 1 for main query, 1 for content_objects since they
        # all use the same table, and 1 for the 'read_by' relation.
        with self.assertNumQueries(3):
            # If we limit to books, we know that they will have 'read_by'
            # attributes, so the following makes sense:
            qs = TaggedItem.objects.filter(content_type=ct, tag='awesome').prefetch_related('content_object__read_by')
            readers_of_awesome_books = set([r.name for tag in qs
                                            for r in tag.content_object.read_by.all()])
            self.assertEqual(readers_of_awesome_books, set(["me", "you", "someone"]))

    def test_nullable_GFK(self):
        TaggedItem.objects.create(tag="awesome", content_object=self.book1,
                                  created_by=self.reader1)
        TaggedItem.objects.create(tag="great", content_object=self.book2)
        TaggedItem.objects.create(tag="rubbish", content_object=self.book3)

        with self.assertNumQueries(2):
            result = [t.created_by for t in TaggedItem.objects.prefetch_related('created_by')]

        self.assertEqual(result,
                         [t.created_by for t in TaggedItem.objects.all()])

    def test_generic_relation(self):
        b = Bookmark.objects.create(url='http://www.djangoproject.com/')
        t1 = TaggedItem.objects.create(content_object=b, tag='django')
        t2 = TaggedItem.objects.create(content_object=b, tag='python')

        with self.assertNumQueries(2):
            tags = [t.tag for b in Bookmark.objects.prefetch_related('tags')
                    for t in b.tags.all()]
            self.assertEqual(sorted(tags), ["django", "python"])

    def test_charfield_GFK(self):
        b = Bookmark.objects.create(url='http://www.djangoproject.com/')
        t1 = TaggedItem.objects.create(content_object=b, tag='django')
        t2 = TaggedItem.objects.create(content_object=b, favorite=b, tag='python')

        with self.assertNumQueries(3):
            bookmark = Bookmark.objects.filter(pk=b.pk).prefetch_related('tags', 'favorite_tags')[0]
            self.assertEqual(sorted([i.tag for i in bookmark.tags.all()]), ["django", "python"])
            self.assertEqual([i.tag for i in bookmark.favorite_tags.all()], ["python"])


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
        self.br1 = BookReview.objects.create(
            book=self.book1, notes="review book1")
        self.br2 = BookReview.objects.create(
            book=self.book2, notes="review book2")

    def test_foreignkey(self):
        with self.assertNumQueries(2):
            qs = AuthorWithAge.objects.prefetch_related('addresses')
            addresses = [[six.text_type(address) for address in obj.addresses.all()]
                         for obj in qs]
        self.assertEqual(addresses, [[six.text_type(self.authorAddress)], [], []])

    def test_foreignkey_to_inherited(self):
        with self.assertNumQueries(2):
            qs = BookReview.objects.prefetch_related('book')
            titles = [obj.book.title for obj in qs]
        self.assertEqual(titles, ["Poems", "More poems"])

    def test_m2m_to_inheriting_model(self):
        qs = AuthorWithAge.objects.prefetch_related('books_with_year')
        with self.assertNumQueries(2):
            lst = [[six.text_type(book) for book in author.books_with_year.all()]
                   for author in qs]
        qs = AuthorWithAge.objects.all()
        lst2 = [[six.text_type(book) for book in author.books_with_year.all()]
                for author in qs]
        self.assertEqual(lst, lst2)

        qs = BookWithYear.objects.prefetch_related('aged_authors')
        with self.assertNumQueries(2):
            lst = [[six.text_type(author) for author in book.aged_authors.all()]
                   for book in qs]
        qs = BookWithYear.objects.all()
        lst2 = [[six.text_type(author) for author in book.aged_authors.all()]
               for book in qs]
        self.assertEqual(lst, lst2)

    def test_parent_link_prefetch(self):
        with self.assertNumQueries(2):
            [a.author for a in AuthorWithAge.objects.prefetch_related('author')]

    @override_settings(DEBUG=True)
    def test_child_link_prefetch(self):
        with self.assertNumQueries(2):
            l = [a.authorwithage for a in Author.objects.prefetch_related('authorwithage')]

        # Regression for #18090: the prefetching query must include an IN clause.
        # Note that on Oracle the table name is upper case in the generated SQL,
        # thus the .lower() call.
        self.assertIn('authorwithage', connection.queries[-1]['sql'].lower())
        self.assertIn(' IN ', connection.queries[-1]['sql'])

        self.assertEqual(l, [a.authorwithage for a in Author.objects.all()])


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
            addresses = [[six.text_type(address) for address in obj.addresses.all()]
                         for obj in qs]
        self.assertEqual(addresses, [[six.text_type(self.authorAddress)], [], []])

    def test_m2m(self):
        with self.assertNumQueries(3):
            qs = Author.objects.all().prefetch_related('favorite_authors', 'favors_me')
            favorites = [(
                 [six.text_type(i_like) for i_like in author.favorite_authors.all()],
                 [six.text_type(likes_me) for likes_me in author.favors_me.all()]
                ) for author in qs]
            self.assertEqual(
                favorites,
                [
                    ([six.text_type(self.author2)],[six.text_type(self.author3)]),
                    ([six.text_type(self.author3)],[six.text_type(self.author1)]),
                    ([six.text_type(self.author1)],[six.text_type(self.author2)])
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
        # Because we use select_related() for 'boss', it doesn't need to be
        # prefetched, but we can still traverse it although it contains some nulls
        with self.assertNumQueries(2):
            qs = Employee.objects.select_related('boss').prefetch_related('boss__serfs')
            co_serfs = [list(e.boss.serfs.all()) if e.boss is not None else []
                        for e in qs]

        qs2 =  Employee.objects.select_related('boss')
        co_serfs2 =  [list(e.boss.serfs.all()) if e.boss is not None else []
                        for e in qs2]

        self.assertEqual(co_serfs, co_serfs2)

    def test_prefetch_nullable(self):
        # One for main employee, one for boss, one for serfs
        with self.assertNumQueries(3):
            qs = Employee.objects.prefetch_related('boss__serfs')
            co_serfs = [list(e.boss.serfs.all()) if e.boss is not None else []
                        for e in qs]

        qs2 =  Employee.objects.all()
        co_serfs2 =  [list(e.boss.serfs.all()) if e.boss is not None else []
                        for e in qs2]

        self.assertEqual(co_serfs, co_serfs2)

    def test_in_bulk(self):
        """
        In-bulk does correctly prefetch objects by not using .iterator()
        directly.
        """
        boss1 = Employee.objects.create(name="Peter")
        boss2 = Employee.objects.create(name="Jack")
        with self.assertNumQueries(2):
            # Check that prefetch is done and it does not cause any errors.
            bulk = Employee.objects.prefetch_related('serfs').in_bulk([boss1.pk, boss2.pk])
            for b in bulk.values():
                list(b.serfs.all())


class MultiDbTests(TestCase):
    multi_db = True

    def test_using_is_honored_m2m(self):
        B = Book.objects.using('other')
        A = Author.objects.using('other')
        book1 = B.create(title="Poems")
        book2 = B.create(title="Jane Eyre")
        book3 = B.create(title="Wuthering Heights")
        book4 = B.create(title="Sense and Sensibility")

        author1 = A.create(name="Charlotte", first_book=book1)
        author2 = A.create(name="Anne", first_book=book1)
        author3 = A.create(name="Emily", first_book=book1)
        author4 = A.create(name="Jane", first_book=book4)

        book1.authors.add(author1, author2, author3)
        book2.authors.add(author1)
        book3.authors.add(author3)
        book4.authors.add(author4)

        # Forward
        qs1 = B.prefetch_related('authors')
        with self.assertNumQueries(2, using='other'):
            books = "".join(["%s (%s)\n" %
                             (book.title, ", ".join(a.name for a in book.authors.all()))
                             for book in qs1])
        self.assertEqual(books,
                         "Poems (Charlotte, Anne, Emily)\n"
                         "Jane Eyre (Charlotte)\n"
                         "Wuthering Heights (Emily)\n"
                         "Sense and Sensibility (Jane)\n")

        # Reverse
        qs2 = A.prefetch_related('books')
        with self.assertNumQueries(2, using='other'):
            authors = "".join(["%s: %s\n" %
                               (author.name, ", ".join(b.title for b in author.books.all()))
                               for author in qs2])
        self.assertEqual(authors,
                          "Charlotte: Poems, Jane Eyre\n"
                          "Anne: Poems\n"
                          "Emily: Poems, Wuthering Heights\n"
                          "Jane: Sense and Sensibility\n")

    def test_using_is_honored_fkey(self):
        B = Book.objects.using('other')
        A = Author.objects.using('other')
        book1 = B.create(title="Poems")
        book2 = B.create(title="Sense and Sensibility")

        author1 = A.create(name="Charlotte Bronte", first_book=book1)
        author2 = A.create(name="Jane Austen", first_book=book2)

        # Forward
        with self.assertNumQueries(2, using='other'):
            books = ", ".join(a.first_book.title for a in A.prefetch_related('first_book'))
        self.assertEqual("Poems, Sense and Sensibility", books)

        # Reverse
        with self.assertNumQueries(2, using='other'):
            books = "".join("%s (%s)\n" %
                            (b.title, ", ".join(a.name for a in b.first_time_authors.all()))
                            for b in B.prefetch_related('first_time_authors'))
        self.assertEqual(books,
                         "Poems (Charlotte Bronte)\n"
                         "Sense and Sensibility (Jane Austen)\n")

    def test_using_is_honored_inheritance(self):
        B = BookWithYear.objects.using('other')
        A = AuthorWithAge.objects.using('other')
        book1 = B.create(title="Poems", published_year=2010)
        book2 = B.create(title="More poems", published_year=2011)
        author1 = A.create(name='Jane', first_book=book1, age=50)
        author2 = A.create(name='Tom', first_book=book1, age=49)

        # parent link
        with self.assertNumQueries(2, using='other'):
            authors = ", ".join(a.author.name for a in A.prefetch_related('author'))

        self.assertEqual(authors, "Jane, Tom")

        # child link
        with self.assertNumQueries(2, using='other'):
            ages = ", ".join(str(a.authorwithage.age) for a in A.prefetch_related('authorwithage'))

        self.assertEqual(ages, "50, 49")


class Ticket19607Tests(TestCase):

    def setUp(self):

        for id, name1, name2 in [
            (1, 'einfach', 'simple'),
            (2, 'schwierig', 'difficult'),
            ]:
            LessonEntry.objects.create(id=id, name1=name1, name2=name2)

        for id, lesson_entry_id, name in [
            (1, 1, 'einfach'),
            (2, 1, 'simple'),
            (3, 2, 'schwierig'),
            (4, 2, 'difficult'),
            ]:
            WordEntry.objects.create(id=id, lesson_entry_id=lesson_entry_id, name=name)

    def test_bug(self):
        list(WordEntry.objects.prefetch_related('lesson_entry', 'lesson_entry__wordentry_set'))


class Ticket21410Tests(TestCase):

    def setUp(self):
        self.book1 = Book.objects.create(title="Poems")
        self.book2 = Book.objects.create(title="Jane Eyre")
        self.book3 = Book.objects.create(title="Wuthering Heights")
        self.book4 = Book.objects.create(title="Sense and Sensibility")

        self.author1 = Author2.objects.create(name="Charlotte",
                                             first_book=self.book1)
        self.author2 = Author2.objects.create(name="Anne",
                                             first_book=self.book1)
        self.author3 = Author2.objects.create(name="Emily",
                                             first_book=self.book1)
        self.author4 = Author2.objects.create(name="Jane",
                                             first_book=self.book4)

        self.author1.favorite_books.add(self.book1, self.book2, self.book3)
        self.author2.favorite_books.add(self.book1)
        self.author3.favorite_books.add(self.book2)
        self.author4.favorite_books.add(self.book3)

    def test_bug(self):
        list(Author2.objects.prefetch_related('first_book', 'favorite_books'))


class Ticket21760Tests(TestCase):

    def setUp(self):
        self.rooms = []
        for _ in range(3):
            house = House.objects.create()
            for _ in range(3):
                self.rooms.append(Room.objects.create(house = house))

    def test_bug(self):
        prefetcher = get_prefetcher(self.rooms[0], 'house')[0]
        queryset = prefetcher.get_prefetch_queryset(list(Room.objects.all()))[0]
        self.assertNotIn(' JOIN ', force_text(queryset.query))
