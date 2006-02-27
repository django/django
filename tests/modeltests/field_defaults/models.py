"""
XXX. Callable defaults

???
"""

from django.db import models
from datetime import datetime

class Article(models.Model):
    headline = models.CharField(maxlength=100, default='Default headline')
    pub_date = models.DateTimeField(default = datetime.now)
    
    def __repr__(self):
        return self.headline

API_TESTS = """
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
'Default headline'

# make sure the two dates are sufficiently close
>>> d = now - a.pub_date
>>> d.seconds < 5
True


"""
