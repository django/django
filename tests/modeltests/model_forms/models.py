"""
XX. Generating HTML forms from models

This is mostly just a reworking of the ``form_for_model``/``form_for_instance``
tests to use ``ModelForm``. As such, the text may not make sense in all cases,
and the examples are probably a poor fit for the ``ModelForm`` syntax. In other
words, most of these tests should be rewritten.
"""

import os
import tempfile

from django.db import models
from django.core.files.storage import FileSystemStorage

# Python 2.3 doesn't have sorted()
try:
    sorted
except NameError:
    from django.utils.itercompat import sorted

temp_storage_dir = tempfile.mkdtemp()
temp_storage = FileSystemStorage(temp_storage_dir)

ARTICLE_STATUS = (
    (1, 'Draft'),
    (2, 'Pending'),
    (3, 'Live'),
)

ARTICLE_STATUS_CHAR = (
    ('d', 'Draft'),
    ('p', 'Pending'),
    ('l', 'Live'),
)

class Category(models.Model):
    name = models.CharField(max_length=20)
    slug = models.SlugField(max_length=20)
    url = models.CharField('The URL', max_length=40)

    def __unicode__(self):
        return self.name

class Writer(models.Model):
    name = models.CharField(max_length=50, help_text='Use both first and last names.')

    def __unicode__(self):
        return self.name

class Article(models.Model):
    headline = models.CharField(max_length=50)
    slug = models.SlugField()
    pub_date = models.DateField()
    created = models.DateField(editable=False)
    writer = models.ForeignKey(Writer)
    article = models.TextField()
    categories = models.ManyToManyField(Category, blank=True)
    status = models.PositiveIntegerField(choices=ARTICLE_STATUS, blank=True, null=True)

    def save(self):
        import datetime
        if not self.id:
            self.created = datetime.date.today()
        return super(Article, self).save()

    def __unicode__(self):
        return self.headline

class ImprovedArticle(models.Model):
    article = models.OneToOneField(Article)

class ImprovedArticleWithParentLink(models.Model):
    article = models.OneToOneField(Article, parent_link=True)

class BetterWriter(Writer):
    pass

class WriterProfile(models.Model):
    writer = models.OneToOneField(Writer, primary_key=True)
    age = models.PositiveIntegerField()

    def __unicode__(self):
        return "%s is %s" % (self.writer, self.age)

from django.contrib.localflavor.us.models import PhoneNumberField
class PhoneNumber(models.Model):
    phone = PhoneNumberField()
    description = models.CharField(max_length=20)

    def __unicode__(self):
        return self.phone

class TextFile(models.Model):
    description = models.CharField(max_length=20)
    file = models.FileField(storage=temp_storage, upload_to='tests')

    def __unicode__(self):
        return self.description

class ImageFile(models.Model):
    def custom_upload_path(self, filename):
        path = self.path or 'tests'
        return '%s/%s' % (path, filename)
    
    description = models.CharField(max_length=20)
    try:
        # If PIL is available, try testing PIL.
        # Checking for the existence of Image is enough for CPython, but
        # for PyPy, you need to check for the underlying modules
        # If PIL is not available, this test is equivalent to TextFile above.
        from PIL import Image, _imaging
        image = models.ImageField(storage=temp_storage, upload_to=custom_upload_path)
    except ImportError:
        image = models.FileField(storage=temp_storage, upload_to=custom_upload_path)
    path = models.CharField(max_length=16, blank=True, default='')

    def __unicode__(self):
        return self.description

class CommaSeparatedInteger(models.Model):
    field = models.CommaSeparatedIntegerField(max_length=20)

    def __unicode__(self):
        return self.field

class Product(models.Model):
    slug = models.SlugField(unique=True)

    def __unicode__(self):
        return self.slug

class Price(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __unicode__(self):
        return u"%s for %s" % (self.quantity, self.price)

    class Meta:
        unique_together = (('price', 'quantity'),)

class ArticleStatus(models.Model):
    status = models.CharField(max_length=2, choices=ARTICLE_STATUS_CHAR, blank=True, null=True)

class Inventory(models.Model):
   barcode = models.PositiveIntegerField(unique=True)
   parent = models.ForeignKey('self', to_field='barcode', blank=True, null=True)
   name = models.CharField(blank=False, max_length=20)

   def __unicode__(self):
      return self.name

class Book(models.Model):
    title = models.CharField(max_length=40)
    author = models.ForeignKey(Writer, blank=True, null=True)
    special_id = models.IntegerField(blank=True, null=True, unique=True)
    
    class Meta:
        unique_together = ('title', 'author')
        
class ExplicitPK(models.Model):
    key = models.CharField(max_length=20, primary_key=True)
    desc = models.CharField(max_length=20, blank=True, unique=True)
    class Meta:
        unique_together = ('key', 'desc')
    
    def __unicode__(self):
        return self.key

__test__ = {'API_TESTS': """
>>> from django import forms
>>> from django.forms.models import ModelForm, model_to_dict
>>> from django.core.files.uploadedfile import SimpleUploadedFile

The bare bones, absolutely nothing custom, basic case.

>>> class CategoryForm(ModelForm):
...     class Meta:
...         model = Category
>>> CategoryForm.base_fields.keys()
['name', 'slug', 'url']


Extra fields.

>>> class CategoryForm(ModelForm):
...     some_extra_field = forms.BooleanField()
...
...     class Meta:
...         model = Category

>>> CategoryForm.base_fields.keys()
['name', 'slug', 'url', 'some_extra_field']

Extra field that has a name collision with a related object accessor.

>>> class WriterForm(ModelForm):
...     book = forms.CharField(required=False)
...
...     class Meta:
...         model = Writer

>>> wf = WriterForm({'name': 'Richard Lockridge'})
>>> wf.is_valid()
True

Replacing a field.

>>> class CategoryForm(ModelForm):
...     url = forms.BooleanField()
...
...     class Meta:
...         model = Category

>>> CategoryForm.base_fields['url'].__class__
<class 'django.forms.fields.BooleanField'>


Using 'fields'.

>>> class CategoryForm(ModelForm):
...
...     class Meta:
...         model = Category
...         fields = ['url']

>>> CategoryForm.base_fields.keys()
['url']


Using 'exclude'

>>> class CategoryForm(ModelForm):
...
...     class Meta:
...         model = Category
...         exclude = ['url']

>>> CategoryForm.base_fields.keys()
['name', 'slug']


Using 'fields' *and* 'exclude'. Not sure why you'd want to do this, but uh,
"be liberal in what you accept" and all.

>>> class CategoryForm(ModelForm):
...
...     class Meta:
...         model = Category
...         fields = ['name', 'url']
...         exclude = ['url']

>>> CategoryForm.base_fields.keys()
['name']

Don't allow more than one 'model' definition in the inheritance hierarchy.
Technically, it would generate a valid form, but the fact that the resulting
save method won't deal with multiple objects is likely to trip up people not
familiar with the mechanics.

>>> class CategoryForm(ModelForm):
...     class Meta:
...         model = Category

>>> class OddForm(CategoryForm):
...     class Meta:
...         model = Article

OddForm is now an Article-related thing, because BadForm.Meta overrides
CategoryForm.Meta.
>>> OddForm.base_fields.keys()
['headline', 'slug', 'pub_date', 'writer', 'article', 'status', 'categories']

>>> class ArticleForm(ModelForm):
...     class Meta:
...         model = Article

First class with a Meta class wins.

>>> class BadForm(ArticleForm, CategoryForm):
...     pass
>>> OddForm.base_fields.keys()
['headline', 'slug', 'pub_date', 'writer', 'article', 'status', 'categories']

Subclassing without specifying a Meta on the class will use the parent's Meta
(or the first parent in the MRO if there are multiple parent classes).

>>> class CategoryForm(ModelForm):
...     class Meta:
...         model = Category
>>> class SubCategoryForm(CategoryForm):
...     pass
>>> SubCategoryForm.base_fields.keys()
['name', 'slug', 'url']

We can also subclass the Meta inner class to change the fields list.

>>> class CategoryForm(ModelForm):
...     checkbox = forms.BooleanField()
...
...     class Meta:
...         model = Category
>>> class SubCategoryForm(CategoryForm):
...     class Meta(CategoryForm.Meta):
...         exclude = ['url']

>>> print SubCategoryForm()
<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" /></td></tr>
<tr><th><label for="id_slug">Slug:</label></th><td><input id="id_slug" type="text" name="slug" maxlength="20" /></td></tr>
<tr><th><label for="id_checkbox">Checkbox:</label></th><td><input type="checkbox" name="checkbox" id="id_checkbox" /></td></tr>

# Old form_for_x tests #######################################################

>>> from django.forms import ModelForm, CharField
>>> import datetime

>>> Category.objects.all()
[]

>>> class CategoryForm(ModelForm):
...     class Meta:
...         model = Category
>>> f = CategoryForm()
>>> print f
<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" /></td></tr>
<tr><th><label for="id_slug">Slug:</label></th><td><input id="id_slug" type="text" name="slug" maxlength="20" /></td></tr>
<tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" /></td></tr>
>>> print f.as_ul()
<li><label for="id_name">Name:</label> <input id="id_name" type="text" name="name" maxlength="20" /></li>
<li><label for="id_slug">Slug:</label> <input id="id_slug" type="text" name="slug" maxlength="20" /></li>
<li><label for="id_url">The URL:</label> <input id="id_url" type="text" name="url" maxlength="40" /></li>
>>> print f['name']
<input id="id_name" type="text" name="name" maxlength="20" />

>>> f = CategoryForm(auto_id=False)
>>> print f.as_ul()
<li>Name: <input type="text" name="name" maxlength="20" /></li>
<li>Slug: <input type="text" name="slug" maxlength="20" /></li>
<li>The URL: <input type="text" name="url" maxlength="40" /></li>

>>> f = CategoryForm({'name': 'Entertainment', 'slug': 'entertainment', 'url': 'entertainment'})
>>> f.is_valid()
True
>>> f.cleaned_data['url']
u'entertainment'
>>> f.cleaned_data['name']
u'Entertainment'
>>> f.cleaned_data['slug']
u'entertainment'
>>> obj = f.save()
>>> obj
<Category: Entertainment>
>>> Category.objects.all()
[<Category: Entertainment>]

>>> f = CategoryForm({'name': "It's a test", 'slug': 'its-test', 'url': 'test'})
>>> f.is_valid()
True
>>> f.cleaned_data['url']
u'test'
>>> f.cleaned_data['name']
u"It's a test"
>>> f.cleaned_data['slug']
u'its-test'
>>> obj = f.save()
>>> obj
<Category: It's a test>
>>> Category.objects.order_by('name')
[<Category: Entertainment>, <Category: It's a test>]

If you call save() with commit=False, then it will return an object that
hasn't yet been saved to the database. In this case, it's up to you to call
save() on the resulting model instance.
>>> f = CategoryForm({'name': 'Third test', 'slug': 'third-test', 'url': 'third'})
>>> f.is_valid()
True
>>> f.cleaned_data['url']
u'third'
>>> f.cleaned_data['name']
u'Third test'
>>> f.cleaned_data['slug']
u'third-test'
>>> obj = f.save(commit=False)
>>> obj
<Category: Third test>
>>> Category.objects.order_by('name')
[<Category: Entertainment>, <Category: It's a test>]
>>> obj.save()
>>> Category.objects.order_by('name')
[<Category: Entertainment>, <Category: It's a test>, <Category: Third test>]

If you call save() with invalid data, you'll get a ValueError.
>>> f = CategoryForm({'name': '', 'slug': 'not a slug!', 'url': 'foo'})
>>> f.errors['name']
[u'This field is required.']
>>> f.errors['slug']
[u"Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens."]
>>> f.cleaned_data
Traceback (most recent call last):
...
AttributeError: 'CategoryForm' object has no attribute 'cleaned_data'
>>> f.save()
Traceback (most recent call last):
...
ValueError: The Category could not be created because the data didn't validate.
>>> f = CategoryForm({'name': '', 'slug': '', 'url': 'foo'})
>>> f.save()
Traceback (most recent call last):
...
ValueError: The Category could not be created because the data didn't validate.

Create a couple of Writers.
>>> w = Writer(name='Mike Royko')
>>> w.save()
>>> w = Writer(name='Bob Woodward')
>>> w.save()

ManyToManyFields are represented by a MultipleChoiceField, ForeignKeys and any
fields with the 'choices' attribute are represented by a ChoiceField.
>>> class ArticleForm(ModelForm):
...     class Meta:
...         model = Article
>>> f = ArticleForm(auto_id=False)
>>> print f
<tr><th>Headline:</th><td><input type="text" name="headline" maxlength="50" /></td></tr>
<tr><th>Slug:</th><td><input type="text" name="slug" maxlength="50" /></td></tr>
<tr><th>Pub date:</th><td><input type="text" name="pub_date" /></td></tr>
<tr><th>Writer:</th><td><select name="writer">
<option value="" selected="selected">---------</option>
<option value="1">Mike Royko</option>
<option value="2">Bob Woodward</option>
</select></td></tr>
<tr><th>Article:</th><td><textarea rows="10" cols="40" name="article"></textarea></td></tr>
<tr><th>Status:</th><td><select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></td></tr>
<tr><th>Categories:</th><td><select multiple="multiple" name="categories">
<option value="1">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third test</option>
</select><br /> Hold down "Control", or "Command" on a Mac, to select more than one.</td></tr>

You can restrict a form to a subset of the complete list of fields
by providing a 'fields' argument. If you try to save a
model created with such a form, you need to ensure that the fields
that are _not_ on the form have default values, or are allowed to have
a value of None. If a field isn't specified on a form, the object created
from the form can't provide a value for that field!
>>> class PartialArticleForm(ModelForm):
...     class Meta:
...         model = Article
...         fields = ('headline','pub_date')
>>> f = PartialArticleForm(auto_id=False)
>>> print f
<tr><th>Headline:</th><td><input type="text" name="headline" maxlength="50" /></td></tr>
<tr><th>Pub date:</th><td><input type="text" name="pub_date" /></td></tr>

When the ModelForm is passed an instance, that instance's current values are
inserted as 'initial' data in each Field.
>>> w = Writer.objects.get(name='Mike Royko')
>>> class RoykoForm(ModelForm):
...     class Meta:
...         model = Writer
>>> f = RoykoForm(auto_id=False, instance=w)
>>> print f
<tr><th>Name:</th><td><input type="text" name="name" value="Mike Royko" maxlength="50" /><br />Use both first and last names.</td></tr>

>>> art = Article(headline='Test article', slug='test-article', pub_date=datetime.date(1988, 1, 4), writer=w, article='Hello.')
>>> art.save()
>>> art.id
1
>>> class TestArticleForm(ModelForm):
...     class Meta:
...         model = Article
>>> f = TestArticleForm(auto_id=False, instance=art)
>>> print f.as_ul()
<li>Headline: <input type="text" name="headline" value="Test article" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" value="test-article" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>
<li>Writer: <select name="writer">
<option value="">---------</option>
<option value="1" selected="selected">Mike Royko</option>
<option value="2">Bob Woodward</option>
</select></li>
<li>Article: <textarea rows="10" cols="40" name="article">Hello.</textarea></li>
<li>Status: <select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="1">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third test</option>
</select>  Hold down "Control", or "Command" on a Mac, to select more than one.</li>
>>> f = TestArticleForm({'headline': u'Test headline', 'slug': 'test-headline', 'pub_date': u'1984-02-06', 'writer': u'1', 'article': 'Hello.'}, instance=art)
>>> f.is_valid()
True
>>> test_art = f.save()
>>> test_art.id
1
>>> test_art = Article.objects.get(id=1)
>>> test_art.headline
u'Test headline'

You can create a form over a subset of the available fields
by specifying a 'fields' argument to form_for_instance.
>>> class PartialArticleForm(ModelForm):
...     class Meta:
...         model = Article
...         fields=('headline', 'slug', 'pub_date')
>>> f = PartialArticleForm({'headline': u'New headline', 'slug': 'new-headline', 'pub_date': u'1988-01-04'}, auto_id=False, instance=art)
>>> print f.as_ul()
<li>Headline: <input type="text" name="headline" value="New headline" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" value="new-headline" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>
>>> f.is_valid()
True
>>> new_art = f.save()
>>> new_art.id
1
>>> new_art = Article.objects.get(id=1)
>>> new_art.headline
u'New headline'

Add some categories and test the many-to-many form output.
>>> new_art.categories.all()
[]
>>> new_art.categories.add(Category.objects.get(name='Entertainment'))
>>> new_art.categories.all()
[<Category: Entertainment>]
>>> class TestArticleForm(ModelForm):
...     class Meta:
...         model = Article
>>> f = TestArticleForm(auto_id=False, instance=new_art)
>>> print f.as_ul()
<li>Headline: <input type="text" name="headline" value="New headline" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" value="new-headline" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>
<li>Writer: <select name="writer">
<option value="">---------</option>
<option value="1" selected="selected">Mike Royko</option>
<option value="2">Bob Woodward</option>
</select></li>
<li>Article: <textarea rows="10" cols="40" name="article">Hello.</textarea></li>
<li>Status: <select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="1" selected="selected">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third test</option>
</select>  Hold down "Control", or "Command" on a Mac, to select more than one.</li>

>>> f = TestArticleForm({'headline': u'New headline', 'slug': u'new-headline', 'pub_date': u'1988-01-04',
...     'writer': u'1', 'article': u'Hello.', 'categories': [u'1', u'2']}, instance=new_art)
>>> new_art = f.save()
>>> new_art.id
1
>>> new_art = Article.objects.get(id=1)
>>> new_art.categories.order_by('name')
[<Category: Entertainment>, <Category: It's a test>]

Now, submit form data with no categories. This deletes the existing categories.
>>> f = TestArticleForm({'headline': u'New headline', 'slug': u'new-headline', 'pub_date': u'1988-01-04',
...     'writer': u'1', 'article': u'Hello.'}, instance=new_art)
>>> new_art = f.save()
>>> new_art.id
1
>>> new_art = Article.objects.get(id=1)
>>> new_art.categories.all()
[]

Create a new article, with categories, via the form.
>>> class ArticleForm(ModelForm):
...     class Meta:
...         model = Article
>>> f = ArticleForm({'headline': u'The walrus was Paul', 'slug': u'walrus-was-paul', 'pub_date': u'1967-11-01',
...     'writer': u'1', 'article': u'Test.', 'categories': [u'1', u'2']})
>>> new_art = f.save()
>>> new_art.id
2
>>> new_art = Article.objects.get(id=2)
>>> new_art.categories.order_by('name')
[<Category: Entertainment>, <Category: It's a test>]

Create a new article, with no categories, via the form.
>>> class ArticleForm(ModelForm):
...     class Meta:
...         model = Article
>>> f = ArticleForm({'headline': u'The walrus was Paul', 'slug': u'walrus-was-paul', 'pub_date': u'1967-11-01',
...     'writer': u'1', 'article': u'Test.'})
>>> new_art = f.save()
>>> new_art.id
3
>>> new_art = Article.objects.get(id=3)
>>> new_art.categories.all()
[]

Create a new article, with categories, via the form, but use commit=False.
The m2m data won't be saved until save_m2m() is invoked on the form.
>>> class ArticleForm(ModelForm):
...     class Meta:
...         model = Article
>>> f = ArticleForm({'headline': u'The walrus was Paul', 'slug': 'walrus-was-paul', 'pub_date': u'1967-11-01',
...     'writer': u'1', 'article': u'Test.', 'categories': [u'1', u'2']})
>>> new_art = f.save(commit=False)

# Manually save the instance
>>> new_art.save()
>>> new_art.id
4

# The instance doesn't have m2m data yet
>>> new_art = Article.objects.get(id=4)
>>> new_art.categories.all()
[]

# Save the m2m data on the form
>>> f.save_m2m()
>>> new_art.categories.order_by('name')
[<Category: Entertainment>, <Category: It's a test>]

Here, we define a custom ModelForm. Because it happens to have the same fields as
the Category model, we can just call the form's save() to apply its changes to an
existing Category instance.
>>> class ShortCategory(ModelForm):
...     name = CharField(max_length=5)
...     slug = CharField(max_length=5)
...     url = CharField(max_length=3)
>>> cat = Category.objects.get(name='Third test')
>>> cat
<Category: Third test>
>>> cat.id
3
>>> form = ShortCategory({'name': 'Third', 'slug': 'third', 'url': '3rd'}, instance=cat)
>>> form.save()
<Category: Third>
>>> Category.objects.get(id=3)
<Category: Third>

Here, we demonstrate that choices for a ForeignKey ChoiceField are determined
at runtime, based on the data in the database when the form is displayed, not
the data in the database when the form is instantiated.
>>> class ArticleForm(ModelForm):
...     class Meta:
...         model = Article
>>> f = ArticleForm(auto_id=False)
>>> print f.as_ul()
<li>Headline: <input type="text" name="headline" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" /></li>
<li>Writer: <select name="writer">
<option value="" selected="selected">---------</option>
<option value="1">Mike Royko</option>
<option value="2">Bob Woodward</option>
</select></li>
<li>Article: <textarea rows="10" cols="40" name="article"></textarea></li>
<li>Status: <select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="1">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third</option>
</select>  Hold down "Control", or "Command" on a Mac, to select more than one.</li>
>>> Category.objects.create(name='Fourth', url='4th')
<Category: Fourth>
>>> Writer.objects.create(name='Carl Bernstein')
<Writer: Carl Bernstein>
>>> print f.as_ul()
<li>Headline: <input type="text" name="headline" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" /></li>
<li>Writer: <select name="writer">
<option value="" selected="selected">---------</option>
<option value="1">Mike Royko</option>
<option value="2">Bob Woodward</option>
<option value="3">Carl Bernstein</option>
</select></li>
<li>Article: <textarea rows="10" cols="40" name="article"></textarea></li>
<li>Status: <select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="1">Entertainment</option>
<option value="2">It&#39;s a test</option>
<option value="3">Third</option>
<option value="4">Fourth</option>
</select>  Hold down "Control", or "Command" on a Mac, to select more than one.</li>

# ModelChoiceField ############################################################

>>> from django.forms import ModelChoiceField, ModelMultipleChoiceField

>>> f = ModelChoiceField(Category.objects.all())
>>> list(f.choices)
[(u'', u'---------'), (1, u'Entertainment'), (2, u"It's a test"), (3, u'Third'), (4, u'Fourth')]
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

# Add a Category object *after* the ModelChoiceField has already been
# instantiated. This proves clean() checks the database during clean() rather
# than caching it at time of instantiation.
>>> Category.objects.create(name='Fifth', url='5th')
<Category: Fifth>
>>> f.clean(5)
<Category: Fifth>

# Delete a Category object *after* the ModelChoiceField has already been
# instantiated. This proves clean() checks the database during clean() rather
# than caching it at time of instantiation.
>>> Category.objects.get(url='5th').delete()
>>> f.clean(5)
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. That choice is not one of the available choices.']

>>> f = ModelChoiceField(Category.objects.filter(pk=1), required=False)
>>> print f.clean('')
None
>>> f.clean('')
>>> f.clean('1')
<Category: Entertainment>
>>> f.clean('100')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. That choice is not one of the available choices.']

# queryset can be changed after the field is created.
>>> f.queryset = Category.objects.exclude(name='Fourth')
>>> list(f.choices)
[(u'', u'---------'), (1, u'Entertainment'), (2, u"It's a test"), (3, u'Third')]
>>> f.clean(3)
<Category: Third>
>>> f.clean(4)
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. That choice is not one of the available choices.']

# check that we can safely iterate choices repeatedly
>>> gen_one = list(f.choices)
>>> gen_two = f.choices
>>> gen_one[2]
(2L, u"It's a test")
>>> list(gen_two)
[(u'', u'---------'), (1L, u'Entertainment'), (2L, u"It's a test"), (3L, u'Third')]

# check that we can override the label_from_instance method to print custom labels (#4620)
>>> f.queryset = Category.objects.all()
>>> f.label_from_instance = lambda obj: "category " + str(obj)
>>> list(f.choices)
[(u'', u'---------'), (1L, 'category Entertainment'), (2L, "category It's a test"), (3L, 'category Third'), (4L, 'category Fourth')]

# ModelMultipleChoiceField ####################################################

>>> f = ModelMultipleChoiceField(Category.objects.all())
>>> list(f.choices)
[(1, u'Entertainment'), (2, u"It's a test"), (3, u'Third'), (4, u'Fourth')]
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
>>> f.clean(['100'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 100 is not one of the available choices.']
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a list of values.']

# Add a Category object *after* the ModelMultipleChoiceField has already been
# instantiated. This proves clean() checks the database during clean() rather
# than caching it at time of instantiation.
>>> Category.objects.create(id=6, name='Sixth', url='6th')
<Category: Sixth>
>>> f.clean([6])
[<Category: Sixth>]

# Delete a Category object *after* the ModelMultipleChoiceField has already been
# instantiated. This proves clean() checks the database during clean() rather
# than caching it at time of instantiation.
>>> Category.objects.get(url='6th').delete()
>>> f.clean([6])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 6 is not one of the available choices.']

>>> f = ModelMultipleChoiceField(Category.objects.all(), required=False)
>>> f.clean([])
[]
>>> f.clean(())
[]
>>> f.clean(['10'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 10 is not one of the available choices.']
>>> f.clean(['3', '10'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 10 is not one of the available choices.']
>>> f.clean(['1', '10'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 10 is not one of the available choices.']

# queryset can be changed after the field is created.
>>> f.queryset = Category.objects.exclude(name='Fourth')
>>> list(f.choices)
[(1, u'Entertainment'), (2, u"It's a test"), (3, u'Third')]
>>> f.clean([3])
[<Category: Third>]
>>> f.clean([4])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 4 is not one of the available choices.']
>>> f.clean(['3', '4'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 4 is not one of the available choices.']

>>> f.queryset = Category.objects.all()
>>> f.label_from_instance = lambda obj: "multicategory " + str(obj)
>>> list(f.choices)
[(1L, 'multicategory Entertainment'), (2L, "multicategory It's a test"), (3L, 'multicategory Third'), (4L, 'multicategory Fourth')]

# OneToOneField ###############################################################

>>> class ImprovedArticleForm(ModelForm):
...     class Meta:
...         model = ImprovedArticle
>>> ImprovedArticleForm.base_fields.keys()
['article']

>>> class ImprovedArticleWithParentLinkForm(ModelForm):
...     class Meta:
...         model = ImprovedArticleWithParentLink
>>> ImprovedArticleWithParentLinkForm.base_fields.keys()
[]

>>> bw = BetterWriter(name=u'Joe Better')
>>> bw.save()
>>> sorted(model_to_dict(bw).keys())
['id', 'name', 'writer_ptr']

>>> class WriterProfileForm(ModelForm):
...     class Meta:
...         model = WriterProfile
>>> form = WriterProfileForm()
>>> print form.as_p()
<p><label for="id_writer">Writer:</label> <select name="writer" id="id_writer">
<option value="" selected="selected">---------</option>
<option value="1">Mike Royko</option>
<option value="2">Bob Woodward</option>
<option value="3">Carl Bernstein</option>
<option value="4">Joe Better</option>
</select></p>
<p><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" /></p>

>>> data = {
...     'writer': u'2',
...     'age': u'65',
... }
>>> form = WriterProfileForm(data)
>>> instance = form.save()
>>> instance
<WriterProfile: Bob Woodward is 65>

>>> form = WriterProfileForm(instance=instance)
>>> print form.as_p()
<p><label for="id_writer">Writer:</label> <select name="writer" id="id_writer">
<option value="">---------</option>
<option value="1">Mike Royko</option>
<option value="2" selected="selected">Bob Woodward</option>
<option value="3">Carl Bernstein</option>
<option value="4">Joe Better</option>
</select></p>
<p><label for="id_age">Age:</label> <input type="text" name="age" value="65" id="id_age" /></p>

# PhoneNumberField ############################################################

>>> class PhoneNumberForm(ModelForm):
...     class Meta:
...         model = PhoneNumber
>>> f = PhoneNumberForm({'phone': '(312) 555-1212', 'description': 'Assistance'})
>>> f.is_valid()
True
>>> f.cleaned_data['phone']
u'312-555-1212'
>>> f.cleaned_data['description']
u'Assistance'

# FileField ###################################################################

# File forms.

>>> class TextFileForm(ModelForm):
...     class Meta:
...         model = TextFile

# Test conditions when files is either not given or empty.

>>> f = TextFileForm(data={'description': u'Assistance'})
>>> f.is_valid()
False
>>> f = TextFileForm(data={'description': u'Assistance'}, files={})
>>> f.is_valid()
False

# Upload a file and ensure it all works as expected.

>>> f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test1.txt', 'hello world')})
>>> f.is_valid()
True
>>> type(f.cleaned_data['file'])
<class 'django.core.files.uploadedfile.SimpleUploadedFile'>
>>> instance = f.save()
>>> instance.file
<FieldFile: tests/test1.txt>

>>> instance.file.delete()

>>> f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test1.txt', 'hello world')})
>>> f.is_valid()
True
>>> type(f.cleaned_data['file'])
<class 'django.core.files.uploadedfile.SimpleUploadedFile'>
>>> instance = f.save()
>>> instance.file
<FieldFile: tests/test1.txt>

# Edit an instance that already has the file defined in the model. This will not
# save the file again, but leave it exactly as it is.

>>> f = TextFileForm(data={'description': u'Assistance'}, instance=instance)
>>> f.is_valid()
True
>>> f.cleaned_data['file']
<FieldFile: tests/test1.txt>
>>> instance = f.save()
>>> instance.file
<FieldFile: tests/test1.txt>

# Delete the current file since this is not done by Django.
>>> instance.file.delete()

# Override the file by uploading a new one.

>>> f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test2.txt', 'hello world')}, instance=instance)
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.file
<FieldFile: tests/test2.txt>

# Delete the current file since this is not done by Django.
>>> instance.file.delete()

>>> f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test2.txt', 'hello world')})
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.file
<FieldFile: tests/test2.txt>

# Delete the current file since this is not done by Django.
>>> instance.file.delete()

>>> instance.delete()

# Test the non-required FileField

>>> f = TextFileForm(data={'description': u'Assistance'})
>>> f.fields['file'].required = False
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.file
<FieldFile: None>

>>> f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test3.txt', 'hello world')}, instance=instance)
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.file
<FieldFile: tests/test3.txt>

# Delete the current file since this is not done by Django.
>>> instance.file.delete()
>>> instance.delete()

>>> f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test3.txt', 'hello world')})
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.file
<FieldFile: tests/test3.txt>

# Delete the current file since this is not done by Django.
>>> instance.file.delete()
>>> instance.delete()

# ImageField ###################################################################

# ImageField and FileField are nearly identical, but they differ slighty when
# it comes to validation. This specifically tests that #6302 is fixed for
# both file fields and image fields.

>>> class ImageFileForm(ModelForm):
...     class Meta:
...         model = ImageFile

>>> image_data = open(os.path.join(os.path.dirname(__file__), "test.png"), 'rb').read()

>>> f = ImageFileForm(data={'description': u'An image'}, files={'image': SimpleUploadedFile('test.png', image_data)})
>>> f.is_valid()
True
>>> type(f.cleaned_data['image'])
<class 'django.core.files.uploadedfile.SimpleUploadedFile'>
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test.png>

# Delete the current file since this is not done by Django.
>>> instance.image.delete()

>>> f = ImageFileForm(data={'description': u'An image'}, files={'image': SimpleUploadedFile('test.png', image_data)})
>>> f.is_valid()
True
>>> type(f.cleaned_data['image'])
<class 'django.core.files.uploadedfile.SimpleUploadedFile'>
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test.png>

# Edit an instance that already has the image defined in the model. This will not
# save the image again, but leave it exactly as it is.

>>> f = ImageFileForm(data={'description': u'Look, it changed'}, instance=instance)
>>> f.is_valid()
True
>>> f.cleaned_data['image']
<...FieldFile: tests/test.png>
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test.png>

# Delete the current image since this is not done by Django.

>>> instance.image.delete()

# Override the file by uploading a new one.

>>> f = ImageFileForm(data={'description': u'Changed it'}, files={'image': SimpleUploadedFile('test2.png', image_data)}, instance=instance)
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test2.png>

# Delete the current file since this is not done by Django.
>>> instance.image.delete()
>>> instance.delete()

>>> f = ImageFileForm(data={'description': u'Changed it'}, files={'image': SimpleUploadedFile('test2.png', image_data)})
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test2.png>

# Delete the current file since this is not done by Django.
>>> instance.image.delete()
>>> instance.delete()

# Test the non-required ImageField

>>> f = ImageFileForm(data={'description': u'Test'})
>>> f.fields['image'].required = False
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: None>

>>> f = ImageFileForm(data={'description': u'And a final one'}, files={'image': SimpleUploadedFile('test3.png', image_data)}, instance=instance)
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test3.png>

# Delete the current file since this is not done by Django.
>>> instance.image.delete()
>>> instance.delete()

>>> f = ImageFileForm(data={'description': u'And a final one'}, files={'image': SimpleUploadedFile('test3.png', image_data)})
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test3.png>
>>> instance.delete()

# Test callable upload_to behavior that's dependent on the value of another field in the model
>>> f = ImageFileForm(data={'description': u'And a final one', 'path': 'foo'}, files={'image': SimpleUploadedFile('test4.png', image_data)})
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: foo/test4.png>
>>> instance.delete()

# Media on a ModelForm ########################################################

# Similar to a regular Form class you can define custom media to be used on
# the ModelForm.

>>> class ModelFormWithMedia(ModelForm):
...     class Media:
...         js = ('/some/form/javascript',)
...         css = {
...             'all': ('/some/form/css',)
...         }
...     class Meta:
...         model = PhoneNumber
>>> f = ModelFormWithMedia()
>>> print f.media
<link href="/some/form/css" type="text/css" media="all" rel="stylesheet" />
<script type="text/javascript" src="/some/form/javascript"></script>

>>> class CommaSeparatedIntegerForm(ModelForm):
...    class Meta:
...        model = CommaSeparatedInteger

>>> f = CommaSeparatedIntegerForm().fields['field']
>>> f.clean('1,2,3')
u'1,2,3'
>>> f.clean('1a,2')
Traceback (most recent call last):
...
ValidationError: [u'Enter only digits separated by commas.']
>>> f.clean(',,,,')
u',,,,'
>>> f.clean('1.2')
Traceback (most recent call last):
...
ValidationError: [u'Enter only digits separated by commas.']
>>> f.clean('1,a,2')
Traceback (most recent call last):
...
ValidationError: [u'Enter only digits separated by commas.']
>>> f.clean('1,,2')
u'1,,2'
>>> f.clean('1')
u'1'

# unique/unique_together validation

>>> class ProductForm(ModelForm):
...     class Meta:
...         model = Product
>>> form = ProductForm({'slug': 'teddy-bear-blue'})
>>> form.is_valid()
True
>>> obj = form.save()
>>> obj
<Product: teddy-bear-blue>
>>> form = ProductForm({'slug': 'teddy-bear-blue'})
>>> form.is_valid()
False
>>> form._errors
{'slug': [u'Product with this Slug already exists.']}
>>> form = ProductForm({'slug': 'teddy-bear-blue'}, instance=obj)
>>> form.is_valid()
True

# ModelForm test of unique_together constraint
>>> class PriceForm(ModelForm):
...     class Meta:
...         model = Price
>>> form = PriceForm({'price': '6.00', 'quantity': '1'})
>>> form.is_valid()
True
>>> form.save()
<Price: 1 for 6.00>
>>> form = PriceForm({'price': '6.00', 'quantity': '1'})
>>> form.is_valid()
False
>>> form._errors
{'__all__': [u'Price with this Price and Quantity already exists.']}

>>> class PriceForm(ModelForm):
...     class Meta:
...         model = Price
...         exclude = ('quantity',)
>>> form = PriceForm({'price': '6.00'})
>>> form.is_valid()
True

# Unique & unique together with null values
>>> class BookForm(ModelForm): 
...     class Meta: 
...        model = Book
>>> w = Writer.objects.get(name='Mike Royko')
>>> form = BookForm({'title': 'I May Be Wrong But I Doubt It', 'author' : w.pk})
>>> form.is_valid()
True
>>> form.save()
<Book: Book object>
>>> form = BookForm({'title': 'I May Be Wrong But I Doubt It', 'author' : w.pk})
>>> form.is_valid()
False
>>> form._errors
{'__all__': [u'Book with this Title and Author already exists.']}
>>> form = BookForm({'title': 'I May Be Wrong But I Doubt It'})
>>> form.is_valid()
True
>>> form.save()
<Book: Book object>
>>> form = BookForm({'title': 'I May Be Wrong But I Doubt It'})
>>> form.is_valid()
True

# Test for primary_key being in the form and failing validation.
>>> class ExplicitPKForm(ModelForm):
...     class Meta:
...         model = ExplicitPK
...         fields = ('key', 'desc',)
>>> form = ExplicitPKForm({'key': u'', 'desc': u'' })
>>> form.is_valid()
False

# Ensure keys and blank character strings are tested for uniqueness.
>>> form = ExplicitPKForm({'key': u'key1', 'desc': u''})
>>> form.is_valid()
True
>>> form.save()
<ExplicitPK: key1>
>>> form = ExplicitPKForm({'key': u'key1', 'desc': u''})
>>> form.is_valid()
False
>>> sorted(form.errors.items())
[('__all__', [u'Explicit pk with this Key and Desc already exists.']), ('desc', [u'Explicit pk with this Desc already exists.']), ('key', [u'Explicit pk with this Key already exists.'])]

# Choices on CharField and IntegerField
>>> class ArticleForm(ModelForm):
...     class Meta:
...         model = Article
>>> f = ArticleForm()
>>> f.fields['status'].clean('42')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 42 is not one of the available choices.']

>>> class ArticleStatusForm(ModelForm):
...     class Meta:
...         model = ArticleStatus
>>> f = ArticleStatusForm()
>>> f.fields['status'].clean('z')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. z is not one of the available choices.']

# Foreign keys which use to_field #############################################

>>> apple = Inventory.objects.create(barcode=86, name='Apple')
>>> pear = Inventory.objects.create(barcode=22, name='Pear')
>>> core = Inventory.objects.create(barcode=87, name='Core', parent=apple)

>>> field = ModelChoiceField(Inventory.objects.all(), to_field_name='barcode')
>>> for choice in field.choices:
...     print choice
(u'', u'---------')
(86, u'Apple')
(22, u'Pear')
(87, u'Core')

>>> class InventoryForm(ModelForm):
...     class Meta:
...         model = Inventory
>>> form = InventoryForm(instance=core)
>>> print form['parent']
<select name="parent" id="id_parent">
<option value="">---------</option>
<option value="86" selected="selected">Apple</option>
<option value="22">Pear</option>
<option value="87">Core</option>
</select>

>>> data = model_to_dict(core)
>>> data['parent'] = '22'
>>> form = InventoryForm(data=data, instance=core)
>>> core = form.save()
>>> core.parent
<Inventory: Pear>

# Clean up
>>> import shutil
>>> shutil.rmtree(temp_storage_dir)
"""}
