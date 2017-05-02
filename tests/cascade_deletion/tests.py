from django.db.models.deletion import Collector
from django.test import TestCase

from .models import (
    Article, Author, Book, BookArticle, Comment, CommentReply, Profile,
)


class CascadeDeletionTest(TestCase):
    def test_cascade_sort(self):
        author = Author.objects.create(name="John")
        Profile.objects.create(author=author, mobile="13333333333")
        article = Article.objects.create(author=author)
        comment = Comment.objects.create(article=article, content="content")
        CommentReply.objects.create(comment=comment, content="content")
        book = Book.objects.create(author=author, name="name")
        BookArticle.objects.create(book=book, article=article)
        for i in range(10):
            collector = Collector(using='default')
            collector.collect(Author.objects.filter(pk=author.pk))
            collector.sort()
            self.assertEqual(collector.data.keys(), [Book, Comment, Article, Author])
