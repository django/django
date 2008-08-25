"""
32. Callable defaults

You can pass callable objects as the ``default`` parameter to a field. When
the object is created without an explicit value passed in, Django will call
the method to determine the default value.

This example uses ``datetime.datetime.now`` as the default for the ``pub_date``
field.
"""

from django.db import models
from datetime import datetime

class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField(default=datetime.now)

    def __unicode__(self):
        return self.headline

__test__ = {'API_TESTS':"""
>>> from datetime import datetime

# No articles are in the system yet.
>>> Article.objects.all()
[]

# Create an Article.
>>> a = Article(id=None)

# Grab the current datetime it should be very close to the default that just
# got saved as a.pub_date
>>> now = datetime.now()

# Save it into the database. You have to call save() explicitly.
>>> a.save()

# Now it has an ID. Note it's a long integer, as designated by the trailing "L".
>>> a.id
1L

# Access database columns via Python attributes.
>>> a.headline
u'Default headline'

# make sure the two dates are sufficiently close
>>> d = now - a.pub_date
>>> d.seconds < 5
True

# make sure that SafeString/SafeUnicode fields work
>>> from django.utils.safestring import SafeUnicode, SafeString
>>> a.headline = SafeUnicode(u'SafeUnicode Headline')
>>> a.save()
>>> a.headline = SafeString(u'SafeString Headline')
>>> a.save()
"""}
