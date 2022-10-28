from django.test import TestCase

from .models import Book


class AsyncModelOoperationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s1 = Book.objects.create(
            title="David Copperfield",
        )
        cls.s2 = Book.objects.create(
            title="The Great Gatsby",
        )

    async def test_asave(self):
        book = await Book.objects.aget(title="David Copperfield")
        book.pages = 10
        await book.asave()
        getBook = await Book.objects.aget(title="David Copperfield")
        self.assertEqual(book.pages, getBook.pages)

    async def test_adelete(self):
        book = await Book.objects.aget(title="The Great Gatsby")
        await book.adelete()
        count = await Book.objects.acount()
        self.assertEqual(count, 1)

    async def test_arefresh_from_db(self):
        book = await Book.objects.aget(title="The Great Gatsby")
        await Book.objects.filter(pk=book.pk).aupdate(pages=20)
        await book.arefresh_from_db()
        self.assertEqual(book.pages, 20)
