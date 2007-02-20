"""
34. Generating HTML forms from models

Django provides shortcuts for creating Form objects from a model class and a
model instance.

The function django.newforms.form_for_model() takes a model class and returns
a Form that is tied to the model. This Form works just like any other Form,
with one additional method: save(). The save() method creates an instance
of the model and returns that newly created instance. It saves the instance to
the database if save(commit=True), which is default. If you pass
commit=False, then you'll get the object without committing the changes to the
database.

The function django.newforms.form_for_instance() takes a model instance and
returns a Form that is tied to the instance. This form works just like any
other Form, with one additional method: save(). The save()
method updates the model instance. It also takes a commit=True parameter.

The function django.newforms.save_instance() takes a bound form instance and a
model instance and saves the form's clean_data into the instance. It also takes
a commit=True parameter.
"""

from django.db import models

class Category(models.Model):
    name = models.CharField(maxlength=20)
    url = models.CharField('The URL', maxlength=40)

    def __str__(self):
        return self.name

class Writer(models.Model):
    name = models.CharField(maxlength=50, help_text='Use both first and last names.')

    def __str__(self):
        return self.name

class Article(models.Model):
    headline = models.CharField(maxlength=50)
    pub_date = models.DateField()
    writer = models.ForeignKey(Writer)
    article = models.TextField()
    categories = models.ManyToManyField(Category, blank=True)

    def __str__(self):
        return self.headline

__test__ = {'API_TESTS': """
>>> from django.newforms import form_for_model, form_for_instance, save_instance, BaseForm, Form, CharField
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
>>> f.is_valid()
True
>>> f.clean_data
{'url': u'entertainment', 'name': u'Entertainment'}
>>> obj = f.save()
>>> obj
<Category: Entertainment>
>>> Category.objects.all()
[<Category: Entertainment>]

>>> f = CategoryForm({'name': "It's a test", 'url': 'test'})
>>> f.is_valid()
True
>>> f.clean_data
{'url': u'test', 'name': u"It's a test"}
>>> obj = f.save()
>>> obj
<Category: It's a test>
>>> Category.objects.all()
[<Category: Entertainment>, <Category: It's a test>]

If you call save() with commit=False, then it will return an object that
hasn't yet been saved to the database. In this case, it's up to you to call
save() on the resulting model instance.
>>> f = CategoryForm({'name': 'Third test', 'url': 'third'})
>>> f.is_valid()
True
>>> f.clean_data
{'url': u'third', 'name': u'Third test'}
>>> obj = f.save(commit=False)
>>> obj
<Category: Third test>
>>> Category.objects.all()
[<Category: Entertainment>, <Category: It's a test>]
>>> obj.save()
>>> Category.objects.all()
[<Category: Entertainment>, <Category: It's a test>, <Category: Third test>]

If you call save() with invalid data, you'll get a ValueError.
>>> f = CategoryForm({'name': '', 'url': 'foo'})
>>> f.errors
{'name': [u'This field is required.']}
>>> f.clean_data
Traceback (most recent call last):
...
AttributeError: 'CategoryForm' object has no attribute 'clean_data'
>>> f.save()
Traceback (most recent call last):
...
ValueError: The Category could not be created because the data didn't validate.
>>> f = CategoryForm({'name': '', 'url': 'foo'})
>>> f.save()
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
<tr><th>Article:</th><td><textarea name="article"></textarea></td></tr>
<tr><th>Categories:</th><td><select multiple="multiple" name="categories">
<option value="1">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third test</option>
</select><br /> Hold down "Control", or "Command" on a Mac, to select more than one.</td></tr>

You can pass a custom Form class to form_for_model. Make sure it's a
subclass of BaseForm, not Form.
>>> class CustomForm(BaseForm):
...     def say_hello(self):
...         print 'hello'
>>> CategoryForm = form_for_model(Category, form=CustomForm)
>>> f = CategoryForm()
>>> f.say_hello()
hello

Use form_for_instance to create a Form from a model instance. The difference
between this Form and one created via form_for_model is that the object's
current values are inserted as 'initial' data in each Field.
>>> w = Writer.objects.get(name='Mike Royko')
>>> RoykoForm = form_for_instance(w)
>>> f = RoykoForm(auto_id=False)
>>> print f
<tr><th>Name:</th><td><input type="text" name="name" value="Mike Royko" maxlength="50" /><br />Use both first and last names.</td></tr>

>>> art = Article(headline='Test article', pub_date=datetime.date(1988, 1, 4), writer=w, article='Hello.')
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
<li>Article: <textarea name="article">Hello.</textarea></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="1">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third test</option>
</select>  Hold down "Control", or "Command" on a Mac, to select more than one.</li>
>>> f = TestArticleForm({'headline': u'New headline', 'pub_date': u'1988-01-04', 'writer': u'1', 'article': 'Hello.'})
>>> f.is_valid()
True
>>> new_art = f.save()
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
<li>Article: <textarea name="article">Hello.</textarea></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="1" selected="selected">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third test</option>
</select>  Hold down "Control", or "Command" on a Mac, to select more than one.</li>

>>> f = TestArticleForm({'headline': u'New headline', 'pub_date': u'1988-01-04',
...     'writer': u'1', 'article': u'Hello.', 'categories': [u'1', u'2']})
>>> new_art = f.save()
>>> new_art.id
1
>>> new_art = Article.objects.get(id=1)
>>> new_art.categories.all()
[<Category: Entertainment>, <Category: It's a test>]

Now, submit form data with no categories. This deletes the existing categories.
>>> f = TestArticleForm({'headline': u'New headline', 'pub_date': u'1988-01-04',
...     'writer': u'1', 'article': u'Hello.'})
>>> new_art = f.save()
>>> new_art.id
1
>>> new_art = Article.objects.get(id=1)
>>> new_art.categories.all()
[]

Create a new article, with categories, via the form.
>>> ArticleForm = form_for_model(Article)
>>> f = ArticleForm({'headline': u'The walrus was Paul', 'pub_date': u'1967-11-01',
...     'writer': u'1', 'article': u'Test.', 'categories': [u'1', u'2']})
>>> new_art = f.save()
>>> new_art.id
2
>>> new_art = Article.objects.get(id=2)
>>> new_art.categories.all()
[<Category: Entertainment>, <Category: It's a test>]

Create a new article, with no categories, via the form.
>>> ArticleForm = form_for_model(Article)
>>> f = ArticleForm({'headline': u'The walrus was Paul', 'pub_date': u'1967-11-01',
...     'writer': u'1', 'article': u'Test.'})
>>> new_art = f.save()
>>> new_art.id
3
>>> new_art = Article.objects.get(id=3)
>>> new_art.categories.all()
[]

Here, we define a custom Form. Because it happens to have the same fields as
the Category model, we can use save_instance() to apply its changes to an
existing Category instance.
>>> class ShortCategory(Form):
...     name = CharField(max_length=5)
...     url = CharField(max_length=3)
>>> cat = Category.objects.get(name='Third test')
>>> cat
<Category: Third test>
>>> cat.id
3
>>> sc = ShortCategory({'name': 'Third', 'url': '3rd'})
>>> save_instance(sc, cat)
<Category: Third>
>>> Category.objects.get(id=3)
<Category: Third>

# ModelChoiceField ############################################################

>>> from django.newforms import ModelChoiceField, ModelMultipleChoiceField

>>> f = ModelChoiceField(Category.objects.all())
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(0)
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. That choice is not one of the available choices.']
>>> f.clean(3)
<Category: Third>
>>> f.clean(2)
<Category: It's a test>

>>> f = ModelChoiceField(Category.objects.filter(pk=1), required=False)
>>> print f.clean('')
None
>>> f.clean('')
>>> f.clean('1')
<Category: Entertainment>
>>> f.clean('2')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. That choice is not one of the available choices.']

# ModelMultipleChoiceField ####################################################

>>> f = ModelMultipleChoiceField(Category.objects.all())
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean([])
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean([1])
[<Category: Entertainment>]
>>> f.clean([2])
[<Category: It's a test>]
>>> f.clean(['1'])
[<Category: Entertainment>]
>>> f.clean(['1', '2'])
[<Category: Entertainment>, <Category: It's a test>]
>>> f.clean([1, '2'])
[<Category: Entertainment>, <Category: It's a test>]
>>> f.clean((1, '2'))
[<Category: Entertainment>, <Category: It's a test>]
>>> f.clean(['nonexistent'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. nonexistent is not one of the available choices.']
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a list of values.']
>>> f = ModelMultipleChoiceField(Category.objects.all(), required=False)
>>> f.clean([])
[]
>>> f.clean(())
[]
>>> f.clean(['4'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 4 is not one of the available choices.']
>>> f.clean(['3', '4'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 4 is not one of the available choices.']
>>> f.clean(['1', '5'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 5 is not one of the available choices.']
"""}
