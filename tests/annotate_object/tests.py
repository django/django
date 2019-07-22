import datetime

from decimal import Decimal

from django.test import TestCase

from django.db.models import OuterRef, CharField, Value

from .models import Author, Book, Publisher


class AnnotateObjectTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author_1 = Author.objects.create(name='Adrian Holovaty', age=34)
        cls.publisher_1 = Publisher.objects.create(name='Apress', num_awards=3)

        cls.book_1 = Book.objects.create(
            isbn='159059725', name='The Definitive Guide to Django: Web Development Done Right',
            pages=447, rating=4.5, price=Decimal('30.00'), contact=cls.author_1, publisher=cls.publisher_1,
            pubdate=datetime.date(2007, 12, 6)
        )

    def test_annotate_non_existing_object(self):
        book_1_id = self.book_1.id
        non_existing_author_id = -1000

        book_with_annotated_author = Book.objects\
            .annotate_object(
                field_name='annotated_author',
                queryset=Author.objects.all(),
                related_object_id=non_existing_author_id
            ).get(
                id=book_1_id
            )

        self.assertEqual(book_with_annotated_author, self.book_1)
        self.assertIsNone(getattr(book_with_annotated_author, 'annotated_author', None))

    def test_basic_object_annotation(self):
        book_1_id = self.book_1.id
        book_with_annotated_author = Book.objects\
            .annotate_object(
                field_name='annotated_author',
                queryset=Author.objects.all(),
                related_object_id=OuterRef('contact__id')
            ).get(
                id=book_1_id
            )

        self.assertEqual(book_with_annotated_author, self.book_1)
        self.assertEqual(book_with_annotated_author.annotated_author, self.book_1.contact)

        for key in Author._meta._forward_fields_map.keys():
            self.assertEqual(
                getattr(book_with_annotated_author.annotated_author, key),
                getattr(self.book_1.contact, key),
            )

    def test_preserve_annotated_object_own_annotation(self):
        greeting = 'Hi!'

        book_1_id = self.book_1.id

        author_queryset = Author.objects.annotate(greeting=Value(greeting, output_field=CharField()))

        book_with_annotated_author = Book.objects\
            .annotate_object(
                field_name='annotated_author',
                queryset=author_queryset,
                related_object_id=OuterRef('contact__id')
            ).get(
                id=book_1_id
            )

        self.assertEqual(book_with_annotated_author, self.book_1)
        self.assertEqual(book_with_annotated_author.annotated_author, self.book_1.contact)
        self.assertEqual(greeting, book_with_annotated_author.annotated_author.greeting)

        for key in Author._meta._forward_fields_map.keys():
            self.assertEqual(
                getattr(book_with_annotated_author.annotated_author, key),
                getattr(self.book_1.contact, key),
            )
