"""
XXX. Serialization

``django.core.serializers`` provides interfaces to converting Django querysets
to and from "flat" data (i.e. strings).
"""

from django.db import models

class Category(models.Model):
    name = models.CharField(maxlength=20)

    class Meta:
       ordering = ('name',)

    def __str__(self):
        return self.name

class Author(models.Model):
    name = models.CharField(maxlength=20)

    class Meta:
        ordering = ('name',)
    
    def __str__(self):
        return self.name

class Article(models.Model):
    author = models.ForeignKey(Author)
    headline = models.CharField(maxlength=50)
    pub_date = models.DateTimeField()
    categories = models.ManyToManyField(Category)

    class Meta:
       ordering = ('pub_date',)

    def __str__(self):
        return self.headline

class AuthorProfile(models.Model):
    author = models.OneToOneField(Author)
    date_of_birth = models.DateField()
    
    def __str__(self):
        return "Profile of %s" % self.author

__test__ = {'API_TESTS':"""
# Create some data:
>>> from datetime import datetime
>>> sports = Category(name="Sports")
>>> music = Category(name="Music")
>>> op_ed = Category(name="Op-Ed")
>>> sports.save(); music.save(); op_ed.save()

>>> joe = Author(name="Joe")
>>> jane = Author(name="Jane")
>>> joe.save(); jane.save()

>>> a1 = Article(
...     author = jane,
...     headline = "Poker has no place on ESPN",
...     pub_date = datetime(2006, 6, 16, 11, 00))
>>> a2 = Article(
...     author = joe,
...     headline = "Time to reform copyright",
...     pub_date = datetime(2006, 6, 16, 13, 00))
>>> a1.save(); a2.save()
>>> a1.categories = [sports, op_ed]
>>> a2.categories = [music, op_ed]

# Serialize a queryset to XML
>>> from django.core import serializers
>>> xml = serializers.serialize("xml", Article.objects.all())

# The output is valid XML
>>> from xml.dom import minidom
>>> dom = minidom.parseString(xml)

# Deserializing has a similar interface, except that special DeserializedObject
# instances are returned.  This is because data might have changed in the 
# database since the data was serialized (we'll simulate that below).
>>> for obj in serializers.deserialize("xml", xml):
...     print obj
<DeserializedObject: Poker has no place on ESPN>
<DeserializedObject: Time to reform copyright>

# Deserializing data with different field values doesn't change anything in the
# database until we call save():
>>> xml = xml.replace("Poker has no place on ESPN", "Poker has no place on television")
>>> objs = list(serializers.deserialize("xml", xml))

# Even those I deserialized, the database hasn't been touched
>>> Article.objects.all()
[<Article: Poker has no place on ESPN>, <Article: Time to reform copyright>]

# But when I save, the data changes as you might except.
>>> objs[0].save()
>>> Article.objects.all()
[<Article: Poker has no place on television>, <Article: Time to reform copyright>]

# Django also ships with a built-in JSON serializers
>>> json = serializers.serialize("json", Category.objects.filter(pk=2))
>>> json
'[{"pk": "2", "model": "serializers.category", "fields": {"name": "Music"}}]'

# You can easily create new objects by deserializing data with an empty PK
# (It's easier to demo this with JSON...)
>>> new_author_json = '[{"pk": null, "model": "serializers.author", "fields": {"name": "Bill"}}]'
>>> for obj in serializers.deserialize("json", new_author_json):
...     obj.save()
>>> Author.objects.all()
[<Author: Bill>, <Author: Jane>, <Author: Joe>]

# All the serializers work the same
>>> json = serializers.serialize("json", Article.objects.all())
>>> for obj in serializers.deserialize("json", json):
...     print obj
<DeserializedObject: Poker has no place on television>
<DeserializedObject: Time to reform copyright>

>>> json = json.replace("Poker has no place on television", "Just kidding; I love TV poker")
>>> for obj in serializers.deserialize("json", json):
...     obj.save()

>>> Article.objects.all()
[<Article: Just kidding; I love TV poker>, <Article: Time to reform copyright>]

# If you use your own primary key field (such as a OneToOneField), 
# it doesn't appear in the serialized field list - it replaces the
# pk identifier.
>>> profile = AuthorProfile(author=joe, date_of_birth=datetime(1970,1,1))
>>> profile.save()

>>> json = serializers.serialize("json", AuthorProfile.objects.all())
>>> json
'[{"pk": "1", "model": "serializers.authorprofile", "fields": {"date_of_birth": "1970-01-01"}}]'

>>> for obj in serializers.deserialize("json", json):
...     print obj
<DeserializedObject: Profile of Joe>

# Objects ids can be referenced before they are defined in the serialization data
# However, the deserialization process will need to be contained within a transaction
>>> json = '[{"pk": "3", "model": "serializers.article", "fields": {"headline": "Forward references pose no problem", "pub_date": "2006-06-16 15:00:00", "categories": [4, 1], "author": 4}}, {"pk": "4", "model": "serializers.category", "fields": {"name": "Reference"}}, {"pk": "4", "model": "serializers.author", "fields": {"name": "Agnes"}}]'
>>> from django.db import transaction
>>> transaction.enter_transaction_management()
>>> transaction.managed(True)
>>> for obj in serializers.deserialize("json", json):
...     obj.save()

>>> transaction.commit()
>>> transaction.leave_transaction_management()

>>> article = Article.objects.get(pk=3)
>>> article
<Article: Forward references pose no problem>
>>> article.categories.all()
[<Category: Reference>, <Category: Sports>]
>>> article.author
<Author: Agnes>

"""}
