"""
3. Giving models custom methods and custom managers

Any method you add to a model will be available to instances.
"""

from django.db import models
import datetime

class Article(models.Model):
    headline = models.CharField(maxlength=100)
    pub_date = models.DateField()

    def __repr__(self):
        return self.headline

    def was_published_today(self):
        return self.pub_date == datetime.date.today()

    def get_articles_from_same_day_1(self):
        return Article.objects.get_list(id__ne=self.id, pub_date__exact=self.pub_date)

    def get_articles_from_same_day_2(self):
        """
        Verbose version of get_articles_from_same_day_1, which does a custom
        database query for the sake of demonstration.
        """
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, headline, pub_date
            FROM custom_methods_articles
            WHERE pub_date = %s
                AND id != %s""", [str(self.pub_date), self.id])
        # The asterisk in "(*row)" tells Python to expand the list into
        # positional arguments to Article().
        return [self.__class__(*row) for row in cursor.fetchall()]

API_TESTS = """
# Create a couple of Articles.
>>> from datetime import date
>>> a = Article(id=None, headline='Area man programs in Python', pub_date=date(2005, 7, 27))
>>> a.save()
>>> b = Article(id=None, headline='Beatles reunite', pub_date=date(2005, 7, 27))
>>> b.save()

# Test the custom methods.
>>> a.was_published_today()
False
>>> a.get_articles_from_same_day_1()
[Beatles reunite]
>>> a.get_articles_from_same_day_2()
[Beatles reunite]
>>> b.get_articles_from_same_day_1()
[Area man programs in Python]
>>> b.get_articles_from_same_day_2()
[Area man programs in Python]
"""
