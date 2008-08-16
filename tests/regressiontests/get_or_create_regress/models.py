from django.db import models

class Publisher(models.Model):
    name = models.CharField(max_length=100)

class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    name = models.CharField(max_length=100)
    authors = models.ManyToManyField(Author, related_name='books')
    publisher = models.ForeignKey(Publisher, related_name='books')


__test__ = {'one':"""
#
# RelatedManager
#

# First create a Publisher.
>>> p = Publisher.objects.create(name='Acme Publishing')

# Create a book through the publisher.
>>> book, created = p.books.get_or_create(name='The Book of Ed & Fred')
>>> created
True

# The publisher should have one book.
>>> p.books.count()
1

# Try get_or_create again, this time nothing should be created.
>>> book, created = p.books.get_or_create(name='The Book of Ed & Fred')
>>> created
False

# And the publisher should still have one book.
>>> p.books.count()
1

#
# ManyRelatedManager
#

# Add an author to the book.
>>> ed, created = book.authors.get_or_create(name='Ed')
>>> created
True

# Book should have one author.
>>> book.authors.count()
1

# Try get_or_create again, this time nothing should be created.
>>> ed, created = book.authors.get_or_create(name='Ed')
>>> created
False

# And the book should still have one author.
>>> book.authors.count()
1

# Add a second author to the book.
>>> fred, created = book.authors.get_or_create(name='Fred')
>>> created
True

# The book should have two authors now.
>>> book.authors.count()
2

# Create an Author not tied to any books.
>>> Author.objects.create(name='Ted')
<Author: Author object>

# There should be three Authors in total. The book object should have two.
>>> Author.objects.count()
3
>>> book.authors.count()
2

# Try creating a book through an author.
>>> ed.books.get_or_create(name="Ed's Recipies", publisher=p)
(<Book: Book object>, True)

# Now Ed has two Books, Fred just one.
>>> ed.books.count()
2
>>> fred.books.count()
1
"""}
