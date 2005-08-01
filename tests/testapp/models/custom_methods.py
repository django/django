"""
3. Giving models custom methods and custom module-level functions

Any method you add to a model will be available to instances.

Custom methods have the same namespace as if the model class were defined
in the dynamically-generated module. That is, methods can access
``get_list()``, ``get_object()``, ``AddManipulator``, and all other
module-level objects.

Also, custom methods have access to a few commonly-used objects for
convenience:

    * The ``datetime`` module from Python's standard library.
    * The ``db`` object from ``django.core.db``. This represents the database
      connection, so you can do custom queries via a cursor object.

If your model method starts with "_module_", it'll be a module-level function
instead of a method. Otherwise, custom module-level functions have the same
namespace as custom methods.
"""

from django.core import meta

class Article(meta.Model):
    fields = (
        meta.CharField('headline', maxlength=100),
        meta.DateField('pub_date'),
    )

    def __repr__(self):
        return self.headline

    def was_published_today(self):
        return self.pub_date == datetime.date.today()

    def get_articles_from_same_day_1(self):
        return get_list(id__ne=self.id, pub_date__exact=self.pub_date)

    def get_articles_from_same_day_2(self):
        """
        Verbose version of get_articles_from_same_day_1, which does a custom
        database query for the sake of demonstration.
        """
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, headline, pub_date
            FROM custom_methods_articles
            WHERE pub_date = %s
                AND id != %s""", [str(self.pub_date), self.id])
        # The asterisk in "Article(*row)" tells Python to expand the list into
        # positional arguments to Article().
        return [Article(*row) for row in cursor.fetchall()]

API_TESTS = """
# Create a couple of Articles.
>>> from datetime import datetime
>>> a = articles.Article(id=None, headline='Area man programs in Python', pub_date=datetime(2005, 7, 27))
>>> a.save()
>>> b = articles.Article(id=None, headline='Beatles reunite', pub_date=datetime(2005, 7, 27))
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
