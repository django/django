"""
34. Generating HTML forms from models

Django provides shortcuts for creating Form objects from a model class.
"""

from django.db import models

class Category(models.Model):
    name = models.CharField(maxlength=20)
    url = models.CharField('The URL', maxlength=40)

    def __str__(self):
        return self.name

class Article(models.Model):
    headline = models.CharField(maxlength=50)
    pub_date = models.DateTimeField()
    categories = models.ManyToManyField(Category)

    def __str__(self):
        return self.headline

__test__ = {'API_TESTS': """
>>> from django.newforms import form_for_model
>>> CategoryForm = form_for_model(Category)
>>> f = CategoryForm()
>>> print f
<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" /></td></tr>
<tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" /></td></tr>
>>> print f.as_ul()
<li><label for="id_name">Name:</label> <input id="id_name" type="text" name="name" maxlength="20" /></li>
<li><label for="id_url">The URL:</label> <input id="id_url" type="text" name="url" maxlength="40" /></li>
>>> print f['name']
<input id="id_name" type="text" name="name" maxlength="20" />

>>> f = CategoryForm(auto_id=False)
>>> print f.as_ul()
<li>Name: <input type="text" name="name" maxlength="20" /></li>
<li>The URL: <input type="text" name="url" maxlength="40" /></li>

>>> f = CategoryForm({'name': 'Entertainment', 'url': 'entertainment'})
>>> f.errors
{}
>>> f.clean_data
{'url': u'entertainment', 'name': u'Entertainment'}
"""}
