"""
34. Generating HTML forms from models

Django provides shortcuts for creating Form objects from a model class.

The function django.newforms.form_for_model() takes a model class and returns
a Form that is tied to the model. This Form works just like any other Form,
with one additional method: create(). The create() method creates an instance
of the model and returns that newly created instance. It saves the instance to
the database if create(save=True), which is default. If you pass
create(save=False), then you'll get the object without saving it.
"""

from django.db import models

class Category(models.Model):
    name = models.CharField(maxlength=20)
    url = models.CharField('The URL', maxlength=40)

    def __str__(self):
        return self.name

class Writer(models.Model):
    name = models.CharField(maxlength=50)

    def __str__(self):
        return self.name

class Article(models.Model):
    headline = models.CharField(maxlength=50)
    pub_date = models.DateField()
    writer = models.ForeignKey(Writer)
    categories = models.ManyToManyField(Category, blank=True)

    def __str__(self):
        return self.headline

__test__ = {'API_TESTS': """
>>> from django.newforms import form_for_model, form_for_instance, BaseForm
>>> import datetime

>>> Category.objects.all()
[]

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
>>> obj = f.create()
>>> obj
<Category: Entertainment>
>>> Category.objects.all()
[<Category: Entertainment>]

>>> f = CategoryForm({'name': "It's a test", 'url': 'test'})
>>> f.errors
{}
>>> f.clean_data
{'url': u'test', 'name': u"It's a test"}
>>> obj = f.create()
>>> obj
<Category: It's a test>
>>> Category.objects.all()
[<Category: Entertainment>, <Category: It's a test>]

If you call create() with save=False, then it will return an object that hasn't
yet been saved. In this case, it's up to you to save it.
>>> f = CategoryForm({'name': 'Third test', 'url': 'third'})
>>> f.errors
{}
>>> f.clean_data
{'url': u'third', 'name': u'Third test'}
>>> obj = f.create(save=False)
>>> obj
<Category: Third test>
>>> Category.objects.all()
[<Category: Entertainment>, <Category: It's a test>]
>>> obj.save()
>>> Category.objects.all()
[<Category: Entertainment>, <Category: It's a test>, <Category: Third test>]

If you call create() with invalid data, you'll get a ValueError.
>>> f = CategoryForm({'name': '', 'url': 'foo'})
>>> f.errors
{'name': [u'This field is required.']}
>>> f.clean_data
>>> f.create()
Traceback (most recent call last):
...
ValueError: The Category could not be created because the data didn't validate.
>>> f = CategoryForm({'name': '', 'url': 'foo'})
>>> f.create()
Traceback (most recent call last):
...
ValueError: The Category could not be created because the data didn't validate.

Create a couple of Writers.
>>> w = Writer(name='Mike Royko')
>>> w.save()
>>> w = Writer(name='Bob Woodward')
>>> w.save()

ManyToManyFields are represented by a MultipleChoiceField, and ForeignKeys are
represented by a ChoiceField.
>>> ArticleForm = form_for_model(Article)
>>> f = ArticleForm(auto_id=False)
>>> print f
<tr><th>Headline:</th><td><input type="text" name="headline" maxlength="50" /></td></tr>
<tr><th>Pub date:</th><td><input type="text" name="pub_date" /></td></tr>
<tr><th>Writer:</th><td><select name="writer">
<option value="" selected="selected">---------</option>
<option value="1">Mike Royko</option>
<option value="2">Bob Woodward</option>
</select></td></tr>
<tr><th>Categories:</th><td><select multiple="multiple" name="categories">
<option value="1">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third test</option>
</select></td></tr>

You can pass a custom Form class to form_for_model. Make sure it's a
subclass of BaseForm, not Form.
>>> class CustomForm(BaseForm):
...     def say_hello(self):
...         print 'hello'
>>> CategoryForm = form_for_model(Category, form=CustomForm)
>>> f = CategoryForm()
>>> f.say_hello()
hello

Use form_for_instance to create a Form from a model instance. There are two
differences between this Form and one created via form_for_model. First, the
object's current values are inserted as 'initial' data in each Field. Second,
the Form gets an apply_changes() method instead of a create() method.
>>> w = Writer.objects.get(name='Mike Royko')
>>> RoykoForm = form_for_instance(w)
>>> f = RoykoForm(auto_id=False)
>>> print f
<tr><th>Name:</th><td><input type="text" name="name" value="Mike Royko" maxlength="50" /></td></tr>

>>> art = Article(headline='Test article', pub_date=datetime.date(1988, 1, 4), writer=w)
>>> art.save()
>>> art.id
1
>>> TestArticleForm = form_for_instance(art)
>>> f = TestArticleForm(auto_id=False)
>>> print f.as_ul()
<li>Headline: <input type="text" name="headline" value="Test article" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>
<li>Writer: <select name="writer">
<option value="">---------</option>
<option value="1" selected="selected">Mike Royko</option>
<option value="2">Bob Woodward</option>
</select></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="1">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third test</option>
</select></li>
>>> f = TestArticleForm({'headline': u'New headline', 'pub_date': u'1988-01-04', 'writer': u'1'})
>>> f.is_valid()
True
>>> new_art = f.apply_changes()
>>> new_art.id
1
>>> new_art = Article.objects.get(id=1)
>>> new_art.headline
'New headline'

Add some categories and test the many-to-many form output.
>>> new_art.categories.all()
[]
>>> new_art.categories.add(Category.objects.get(name='Entertainment'))
>>> new_art.categories.all()
[<Category: Entertainment>]
>>> TestArticleForm = form_for_instance(new_art)
>>> f = TestArticleForm(auto_id=False)
>>> print f.as_ul()
<li>Headline: <input type="text" name="headline" value="New headline" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>
<li>Writer: <select name="writer">
<option value="">---------</option>
<option value="1" selected="selected">Mike Royko</option>
<option value="2">Bob Woodward</option>
</select></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="1" selected="selected">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third test</option>
</select></li>

"""}
