"""
34. Generating HTML forms from models

Django provides shortcuts for creating Form objects from a model class.
"""

from django.db import models

class Category(models.Model):
    name = models.CharField(maxlength=20)
    url = models.CharField('The URL', maxlength=20)

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
<tr><th><label for="id_id">ID:</label></th><td><input type="text" name="id" id="id_id" /></td></tr>
<tr><th><label for="id_name">Name:</label></th><td><input type="text" name="name" id="id_name" /></td></tr>
<tr><th><label for="id_url">The URL:</label></th><td><input type="text" name="url" id="id_url" /></td></tr>
>>> print f.as_ul()
<li><label for="id_id">ID:</label> <input type="text" name="id" id="id_id" /></li>
<li><label for="id_name">Name:</label> <input type="text" name="name" id="id_name" /></li>
<li><label for="id_url">The URL:</label> <input type="text" name="url" id="id_url" /></li>
>>> print f['name']
<input type="text" name="name" id="id_name" />

>>> f = CategoryForm(auto_id=False)
>>> print f.as_ul()
<li>ID: <input type="text" name="id" /></li>
<li>Name: <input type="text" name="name" /></li>
<li>The URL: <input type="text" name="url" /></li>
"""}
