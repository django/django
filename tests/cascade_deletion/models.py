"""
Use the same order when cascade deletion
"""

from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)


class Article(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField(auto_now_add=True)


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    content = models.CharField(max_length=1024)


class CommentReply(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    content = models.CharField(max_length=1024)


class Profile(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=100)


class Book(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)


class BookArticle(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    sequence = models.IntegerField(default=0)
