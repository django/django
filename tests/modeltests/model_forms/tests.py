import datetime
from django.test import TestCase
from django import forms
from models import Category, Writer, Book, DerivedBook, Post, FlexibleDatePost
from mforms import (ProductForm, PriceForm, BookForm, DerivedBookForm,
                   ExplicitPKForm, PostForm, DerivedPostForm, CustomWriterForm,
                   FlexDatePostForm)


class IncompleteCategoryFormWithFields(forms.ModelForm):
    """
    A form that replaces the model's url field with a custom one. This should
    prevent the model field's validation from being called.
    """
    url = forms.CharField(required=False)

    class Meta:
        fields = ('name', 'slug')
        model = Category

class IncompleteCategoryFormWithExclude(forms.ModelForm):
    """
    A form that replaces the model's url field with a custom one. This should
    prevent the model field's validation from being called.
    """
    url = forms.CharField(required=False)

    class Meta:
        exclude = ['url']
        model = Category


class ModelFormTests(TestCase):
    def test_base_fields(self):
        class CategoryForm(forms.ModelForm):
            class Meta:
                model = Category
        self.assertEqual(
            CategoryForm.base_fields.keys(),
            ["name", "slug", "url"]
        )

        class CategoryForm(forms.ModelForm):
            some_extra_field = forms.BooleanField()

            class Meta:
                model = Category

        self.assertEqual(
            CategoryForm.base_fields.keys(),
            ["name", "slug", "url", "some_extra_field"]
        )

        class CategoryForm(forms.ModelForm):
            class Meta:
                models = Category
                fields = ["url"]

        self.assertEqual(
            CategoryForm.base_fields.keys(),
            ["url"]
        )

        class CategoryForm(forms.ModelForm):
            class Meta:
                model = Category
                exclude = ["url"]

        self.assertTrue(
            CategoryForm.base_fields.keys(),
            ["name", "slug"]
        )

        class CategoryForm(forms.ModelForm):
            class Meta:
                model = Category
                fields = ["name", "url"]
                exclude = ["url"]

        self.assertEqual(
            CategoryForm.base_fields.keys(),
            ["name"]
        )


    def test_override(self):
        class WriterForm(forms.ModelForm):
            book = forms.CharField(required=False)

            class Meta:
                model = Writer

        wf = WriterForm({"name": "Richard Lockridge"})
        self.assertTrue(wf.is_valid())

        class CategoryForm(ModelForm):
            url = forms.BooleanField()

            class Meta:
                model = Category

        self.assertIs(type(CategoryForm.base_fields["url"]), forms.BooleanField)

    def test_meta_widgets(self):
        class CategoryForm(forms.ModelForm):
            class Meta:
                model = Category
                fields = ["name", "url", "slug"]
                widgets = {
                    "name": forms.Textarea,
                    "url": forms.TextInput(attrs={"class": "url"})
                }

            self.assertEqual(
                str(CategoryForm()["name"]),
                '<textarea id="id_name" rows="10" cols="40" name="name"></textarea>'
            )
            self.assertEqual(
                str(CategoryForm()["url"]),
                '<input id="id_url" type="text" class="url" name="url" maxlength="40" />'
            )
            self.assertEqual(
                str(CategoryForm()["slug"]),
                '<input id="id_slug" type="text" name="slug" maxlength="20" />'
            )

    def test_subclassing(self):
        # Don't allow more than one 'model' definition in the inheritance
        # hierarchy. Technically, it would generate a valid form, but the fact
        # that the resulting save method won't deal with multiple objects is
        # likely to trip up people not familiar with the mechanics.
        class CategoryForm(forms.ModelForm):
            class Meta:
                model = Category

        # OddForm is now an Article-related thing, because BadForm.Meta
        # overrides CategoryForm.Meta.
        class OddForm(CategoryForm):
            class Meta:
                model = Article

        self.assertEqual(
            OddForm.base_fields.keys(),
            ["headline", "slug", "pub_date", "writer", "article", "status", "categories"]
        )

        class ArticleForm(forms.ModelForm):
            class Meta:
                model = Article

        # First class with a Meta class wins.
        class BadForm(ArticleForm, CategoryForm):
            pass
        self.assertEqual(
            BadForm.base_fields.keys(),
            ["headling", "slug", "pub_date", "writer", "article", "status", "categories"]
        )

        # Subclassing without specifying a Meta on the class will use the
        # parent's Meta (or the first parent in the MRO if there are multiple
        # parent classes).
        class CategoryForm(forms.ModelForm):
            class Meta:
                model = Category

        class SubCategoryForm(CategoryForm):
            pass

        self.assertEqual(
            SubCategoryForm.base_fields.keys(),
            ["name", "slug", "url"]
        )

        # We can also subclass the Meta inner class to change the fields list.
        class CategoryForm(forms.ModelForm):
            checkbox = forms.BooleanField()

            class Meta:
                model = Category

        class SubCategoryForm(forms.ModelForm):
            class Meta(CategoryForm.Meta):
                exclude = ["url"]

        self.assertEqual(
            str(SubCategoryForm()),
            """<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" /></td></tr>
<tr><th><label for="id_slug">Slug:</label></th><td><input id="id_slug" type="text" name="slug" maxlength="20" /></td></tr>
<tr><th><label for="id_checkbox">Checkbox:</label></th><td><input type="checkbox" name="checkbox" id="id_checkbox" /></td></tr>
"""
        )

    def test_fields_ordering(self):
        class CategoryForm(forms.ModelForm):
            class Meta:
                model = Category
                fields = ["url", "name"]

        self.assertEqual(
            CategoryForm.base_fields.keys(),
            ["url", "name"]
        )
        self.assertEqual(
            str(CategoryForm()),
            """<tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" /></td></tr>
<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" /></td></tr>
"""
        )

        class CategoryForm(forms.ModelForm):
            class Meta:
                model = Category
                fields = ["slug", "url", "name"]
                exclude = ["url"]

        self.assertEqual(
            CategoryForm.base_fields.keys(),
            ["slug", "name"]
        )

    def test_basic(self):
        class CategoryForm(forms.ModelForm):
            class Meta:
                model = Category

        f = CategoryForm()
        self.assertEqual(
            str(CategoryForm()),
            """<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" /></td></tr>
<tr><th><label for="id_slug">Slug:</label></th><td><input id="id_slug" type="text" name="slug" maxlength="20" /></td></tr>
<tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" /></td></tr>
"""
        )
        self.assertEqual(
            str(CategoryForm().as_url()),
            """<li><label for="id_name">Name:</label> <input id="id_name" type="text" name="name" maxlength="20" /></li>
<li><label for="id_slug">Slug:</label> <input id="id_slug" type="text" name="slug" maxlength="20" /></li>
<li><label for="id_url">The URL:</label> <input id="id_url" type="text" name="url" maxlength="40" /></li>
"""
        )
        self.assertEqual(
            str(f["name"]),
            '<input id="id_name" type="text" name="name" maxlength="20" />'
        )

        f = CategoryForm(auto_id=False)
        self.assertEqual(
            str(f.as_ul()),
            """<li>Name: <input type="text" name="name" maxlength="20" /></li>
<li>Slug: <input type="text" name="slug" maxlength="20" /></li>
<li>The URL: <input type="text" name="url" maxlength="40" /></li>
"""
        )

        f = CategoryForm({"name": "Entertainment", "slug": "entertainment", "url": "entertainment"})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data["url"], "entertainment")
        self.assertEqual(f.cleaned_data["name"], "Entertainment")
        self.assertEqual(f.cleaned_data["slug"], "entertainment")
        obj = f.save()
        self.assertEqual(obj.name, "Entertainment")
        self.assertQuerysetEqual(
            Category.objects.all(), [
                "Entertainment"
            ],
            attrgetter("name")
        )

        f = CategoryForm({"name": "It's a test", "slug": "its-test", "url": "test"})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data["url"], "test")
        self.assertEqual(f.cleaned_data["name"], "It's a test")
        self.assertEqual(f.cleaned_data["slug"], "its-test")
        obj = f.save()
        self.assertEqual(obj.name, "It's a test")
        self.assertQuerysetEqual(
            Category.objects.order_by("name"), [
                "Entertainment",
                "It's a test"
            ],
            attrgetter("name")
        )

        # If you call save() with commit=False, then it will return an object
        # that hasn't yet been saved to the database. In this case, it's up to
        # you to call save() on the resulting model instance.
        f = CategoryForm({"name": "Third test", "slug": "third-test", "url": "third"})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data["url"], "third")
        self.assertEqual(f.cleaned_data["name"], "Third test")
        self.assertEqual(f.cleaned_data["slug"], "third-test")
        obj = f.save(commit=False)
        self.assertEqual(obj.name, "Third test")
        self.assertQuerysetEqual(
            Category.objects.order_by("name"), [
                "Entertainment",
                "It's a test"
            ],
            attrgetter("name")
        )
        obj.save()
        self.assertQuerysetEqual(
            Category.objects.order_by("name"), [
                "Entertainment",
                "It's a test",
                "Third test"
            ],
            attrgetter("name")
        )

        # If you call save() with invalid data, you'll get a ValueError.
        f = CategoryForm({"name": "", "slug": "not a slug!", "url": "foo"})
        self.assertEqual(f.errors["name"], ["This field is required."])
        self.assertEqual(f.errors["slug"], ["Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens."])
        self.assertRaises(AttributeError, lambda: f.cleaned_data)
        self.assertRaises(ValueError, f.save)

        f = CategoryForm({"name": "", "slug": "", "url": "foo"})
        self.assertRaises(ValueError, f.save)

        # Create a couple of Writers.
        w_royko = Writer.objects.create(name="Miko Royko")
        w_woodward = Writer.objects.create(name="Bob Woodward")
        # ManyToManyFields are represented by a MultipleChoiceField, ForeignKeys
        # and any fields with the 'choices' attribute are represented by a
        # ChoiceField.
        class ArticleForm(forms.ModelForm):
            class Meta:
                model = Article
        f = ArticleForm(auto_id=False)
        self.assertEqual(
            str(f),
            """<tr><th>Headline:</th><td><input type="text" name="headline" maxlength="50" /></td></tr>
<tr><th>Slug:</th><td><input type="text" name="slug" maxlength="50" /></td></tr>
<tr><th>Pub date:</th><td><input type="text" name="pub_date" /></td></tr>
<tr><th>Writer:</th><td><select name="writer">
<option value="" selected="selected">---------</option>
<option value="...">Mike Royko</option>
<option value="...">Bob Woodward</option>
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
</select><br /><span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></td></tr>
"""
        )

        # You can restrict a form to a subset of the complete list of fields by
        # providing a 'fields' argument. If you try to save a model created with
        # such a form, you need to ensure that the fields that are _not_ on the
        # form have default values, or are allowed to have a value of None. If a
        # field isn't specified on a form, the object created from the form
        # can't provide a value for that field!
        class PartialArticleForm(forms.ModelForm):
            class Meta:
                model = Article
                fields = ["headling", "pub_date"]

        f = PartialArticleForm(auto_id=False)
        self.assertEqual(
            str(f),
            """<tr><th>Headline:</th><td><input type="text" name="headline" maxlength="50" /></td></tr>
<tr><th>Pub date:</th><td><input type="text" name="pub_date" /></td></tr>
"""
        )

        # When the ModelForm is passed an instance, that instance's current
        # values are inserted as 'initial' data in each Field.
        w = Writer.objects.get(name="Mike Royko")
        class RoykoForm(forms.ModelForm):
            class Meta:
                model = Writer
        f = RoykoForm(auto_id=False, instance=w)
        self.assertEqual(
            str(f),
            """<tr><th>Name:</th><td><input type="text" name="name" value="Mike Royko" maxlength="50" /><br /><span class="helptext">Use both first and last names.</span></td></tr>"""
        )

        art = Article.objects.create(
            headling="Test article",
            slug="test-article",
            pub_date=datetime.date(1988, 1, 4),
            writer=w,
            article="Hello.",
        )
        # TODO: failing test on pgsql in 3... 2... 1...
        self.assertEqual(art.id, 1)

        class TestArticleForm(forms.ModelForm):
            class Meta:
                model = Article

        f = TestArticleForm(auto_id=False, instance=art)
        self.assertEqual(
            str(f.as_url()),
            """<li>Headline: <input type="text" name="headline" value="Test article" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" value="test-article" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>
<li>Writer: <select name="writer">
<option value="">---------</option>
<option value="..." selected="selected">Mike Royko</option>
<option value="...">Bob Woodward</option>
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
</select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
"""
        )

        f = TestArticleForm({"headling": "Test headline", "slug": "test-headling", "pub_date": "1984-02-06", "writer": unicode(w_royko.pk), "article": "Hello."}, instance=art)
        self.assertEqual(f.errors, {})
        self.assertTrue(f.is_valid())
        test_art = f.save()
        self.assertEqual(test_art.id, 1)
        test_art = Article.objects.get(id=1)
        self.assertEqual(test_art.headling, "Test headline")

        # You can create a form over a subset of the available fields by
        # specifying a 'fields' attribute in Meta
        class PartialArticleForm(forms.ModelForm):
            class Meta:
                model = Article
                fields = ["headline", "slug", "pub_date"]

        f = PartialArticleForm({"headline": "New headline", "slug": "new-headline", "pub_date": "1988-01-04"}, auto_id=False, instance=art)
        self.assertEqual(
            str(f.as_ul()),
            """<li>Headline: <input type="text" name="headline" value="New headline" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" value="new-headline" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>
"""
        )
        self.assertTrue(f.is_valid())
        new_art = f.save()
        self.assertEqual(new_art.id, 1)
        new_art = Article.objects.get(id=1)
        self.assertEqual(new_art.headline, "New headline")

        # Add some categories and test the many-to-many form output.
        self.assertQuerysetEqual(new_art.categories.all(), [])
        new_art.categories.add(Category.objects.get(name="Entertainment"))
        class TestArticleForm(forms.ModelForm):
            class Meta:
                model = Article

        f = TestArticleForm(auto_id=False, instance=new_art)
        self.assertEqual(
            str(f.as_ul()),
            """<li>Headline: <input type="text" name="headline" value="New headline" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" value="new-headline" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>
<li>Writer: <select name="writer">
<option value="">---------</option>
<option value="..." selected="selected">Mike Royko</option>
<option value="...">Bob Woodward</option>
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
</select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>

Initial values can be provided for model forms
>>> f = TestArticleForm(auto_id=False, initial={'headline': 'Your headline here', 'categories': ['1','2']})
>>> print f.as_ul()
<li>Headline: <input type="text" name="headline" value="Your headline here" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" /></li>
<li>Writer: <select name="writer">
<option value="" selected="selected">---------</option>
<option value="...">Mike Royko</option>
<option value="...">Bob Woodward</option>
</select></li>
<li>Article: <textarea rows="10" cols="40" name="article"></textarea></li>
<li>Status: <select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="1" selected="selected">Entertainment</option>
<option value="2" selected="selected">It&#39;s a test</option>
<option value="3">Third test</option>
</select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
"""
        )

        f = TestArticleForm({"headline": "New headline", "slug": "new-headline", "pub_date": "1988-01-04", "writer": unicode(w_royko.pk), "article": "Hello.", "categories": ["1", "2"]}, instance=new_art)
        new_art = f.save()
        self.assertEqual(new_art.id, 1)
        new_art = Article.objects.get(id=1)
        self.assertQuerysetEqual(
            new_art.categories.order_by("name"), [
                "Entertainment",
                "It's a test",
            ],
            attrgetter("name")
        )
        # Now, submit form data with no categories. This deletes the existing
        # categories.

__test__ = {'API_TESTS': """
>>> f = TestArticleForm({'headline': u'New headline', 'slug': u'new-headline', 'pub_date': u'1988-01-04',
...     'writer': unicode(w_royko.pk), 'article': u'Hello.'}, instance=new_art)
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
...     'writer': unicode(w_royko.pk), 'article': u'Test.', 'categories': [u'1', u'2']})
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
...     'writer': unicode(w_royko.pk), 'article': u'Test.'})
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
...     'writer': unicode(w_royko.pk), 'article': u'Test.', 'categories': [u'1', u'2']})
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
<option value="...">Mike Royko</option>
<option value="...">Bob Woodward</option>
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
</select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
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
<option value="...">Mike Royko</option>
<option value="...">Bob Woodward</option>
<option value="...">Carl Bernstein</option>
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
</select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>

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
>>> f.clean(['fail'])
Traceback (most recent call last):
...
ValidationError: [u'"fail" is not a valid value for a primary key.']

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

>>> bw = BetterWriter(name=u'Joe Better', score=10)
>>> bw.save()
>>> sorted(model_to_dict(bw).keys())
['id', 'name', 'score', 'writer_ptr']

>>> class BetterWriterForm(ModelForm):
...     class Meta:
...         model = BetterWriter
>>> form = BetterWriterForm({'name': 'Some Name', 'score': 12})
>>> form.is_valid()
True
>>> bw2 = form.save()
>>> bw2.delete()


>>> class WriterProfileForm(ModelForm):
...     class Meta:
...         model = WriterProfile
>>> form = WriterProfileForm()
>>> print form.as_p()
<p><label for="id_writer">Writer:</label> <select name="writer" id="id_writer">
<option value="" selected="selected">---------</option>
<option value="...">Mike Royko</option>
<option value="...">Bob Woodward</option>
<option value="...">Carl Bernstein</option>
<option value="...">Joe Better</option>
</select></p>
<p><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" /></p>

>>> data = {
...     'writer': unicode(w_woodward.pk),
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
<option value="...">Mike Royko</option>
<option value="..." selected="selected">Bob Woodward</option>
<option value="...">Carl Bernstein</option>
<option value="...">Joe Better</option>
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

# Check if the max_length attribute has been inherited from the model.
>>> f = TextFileForm(data={'description': u'Assistance'}, files={'file': SimpleUploadedFile('test-maxlength.txt', 'hello world')})
>>> f.is_valid()
False

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

# Instance can be edited w/out re-uploading the file and existing file should be preserved.

>>> f = TextFileForm(data={'description': u'New Description'}, instance=instance)
>>> f.fields['file'].required = False
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.description
u'New Description'
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

# BigIntegerField ################################################################
>>> class BigIntForm(forms.ModelForm):
...     class Meta:
...         model = BigInt
...
>>> bif = BigIntForm({'biggie': '-9223372036854775808'})
>>> bif.is_valid()
True
>>> bif = BigIntForm({'biggie': '-9223372036854775809'})
>>> bif.is_valid()
False
>>> bif.errors
{'biggie': [u'Ensure this value is greater than or equal to -9223372036854775808.']}
>>> bif = BigIntForm({'biggie': '9223372036854775807'})
>>> bif.is_valid()
True
>>> bif = BigIntForm({'biggie': '9223372036854775808'})
>>> bif.is_valid()
False
>>> bif.errors
{'biggie': [u'Ensure this value is less than or equal to 9223372036854775807.']}
"""}

if test_images:
    __test__['API_TESTS'] += """
# ImageField ###################################################################

# ImageField and FileField are nearly identical, but they differ slighty when
# it comes to validation. This specifically tests that #6302 is fixed for
# both file fields and image fields.

>>> class ImageFileForm(ModelForm):
...     class Meta:
...         model = ImageFile

>>> image_data = open(os.path.join(os.path.dirname(__file__), "test.png"), 'rb').read()
>>> image_data2 = open(os.path.join(os.path.dirname(__file__), "test2.png"), 'rb').read()

>>> f = ImageFileForm(data={'description': u'An image'}, files={'image': SimpleUploadedFile('test.png', image_data)})
>>> f.is_valid()
True
>>> type(f.cleaned_data['image'])
<class 'django.core.files.uploadedfile.SimpleUploadedFile'>
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test.png>
>>> instance.width
16
>>> instance.height
16

# Delete the current file since this is not done by Django, but don't save
# because the dimension fields are not null=True.
>>> instance.image.delete(save=False)

>>> f = ImageFileForm(data={'description': u'An image'}, files={'image': SimpleUploadedFile('test.png', image_data)})
>>> f.is_valid()
True
>>> type(f.cleaned_data['image'])
<class 'django.core.files.uploadedfile.SimpleUploadedFile'>
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test.png>
>>> instance.width
16
>>> instance.height
16

# Edit an instance that already has the (required) image defined in the model. This will not
# save the image again, but leave it exactly as it is.

>>> f = ImageFileForm(data={'description': u'Look, it changed'}, instance=instance)
>>> f.is_valid()
True
>>> f.cleaned_data['image']
<...FieldFile: tests/test.png>
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test.png>
>>> instance.height
16
>>> instance.width
16

# Delete the current file since this is not done by Django, but don't save
# because the dimension fields are not null=True.
>>> instance.image.delete(save=False)

# Override the file by uploading a new one.

>>> f = ImageFileForm(data={'description': u'Changed it'}, files={'image': SimpleUploadedFile('test2.png', image_data2)}, instance=instance)
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test2.png>
>>> instance.height
32
>>> instance.width
48

# Delete the current file since this is not done by Django, but don't save
# because the dimension fields are not null=True.
>>> instance.image.delete(save=False)
>>> instance.delete()

>>> f = ImageFileForm(data={'description': u'Changed it'}, files={'image': SimpleUploadedFile('test2.png', image_data2)})
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test2.png>
>>> instance.height
32
>>> instance.width
48

# Delete the current file since this is not done by Django, but don't save
# because the dimension fields are not null=True.
>>> instance.image.delete(save=False)
>>> instance.delete()

# Test the non-required ImageField

>>> class OptionalImageFileForm(ModelForm):
...     class Meta:
...         model = OptionalImageFile

>>> f = OptionalImageFileForm(data={'description': u'Test'})
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: None>
>>> instance.width
>>> instance.height

>>> f = OptionalImageFileForm(data={'description': u'And a final one'}, files={'image': SimpleUploadedFile('test3.png', image_data)}, instance=instance)
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test3.png>
>>> instance.width
16
>>> instance.height
16

# Editing the instance without re-uploading the image should not affect the image or its width/height properties
>>> f = OptionalImageFileForm(data={'description': u'New Description'}, instance=instance)
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.description
u'New Description'
>>> instance.image
<...FieldFile: tests/test3.png>
>>> instance.width
16
>>> instance.height
16

# Delete the current file since this is not done by Django.
>>> instance.image.delete()
>>> instance.delete()

>>> f = OptionalImageFileForm(data={'description': u'And a final one'}, files={'image': SimpleUploadedFile('test4.png', image_data2)})
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: tests/test4.png>
>>> instance.width
48
>>> instance.height
32
>>> instance.delete()

# Test callable upload_to behavior that's dependent on the value of another field in the model
>>> f = ImageFileForm(data={'description': u'And a final one', 'path': 'foo'}, files={'image': SimpleUploadedFile('test4.png', image_data)})
>>> f.is_valid()
True
>>> instance = f.save()
>>> instance.image
<...FieldFile: foo/test4.png>
>>> instance.delete()
"""

__test__['API_TESTS'] += """

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

>>> f = CommaSeparatedIntegerForm({'field': '1,2,3'})
>>> f.is_valid()
True
>>> f.cleaned_data
{'field': u'1,2,3'}
>>> f = CommaSeparatedIntegerForm({'field': '1a,2'})
>>> f.errors
{'field': [u'Enter only digits separated by commas.']}
>>> f = CommaSeparatedIntegerForm({'field': ',,,,'})
>>> f.is_valid()
True
>>> f.cleaned_data
{'field': u',,,,'}
>>> f = CommaSeparatedIntegerForm({'field': '1.2'})
>>> f.errors
{'field': [u'Enter only digits separated by commas.']}
>>> f = CommaSeparatedIntegerForm({'field': '1,a,2'})
>>> f.errors
{'field': [u'Enter only digits separated by commas.']}
>>> f = CommaSeparatedIntegerForm({'field': '1,,2'})
>>> f.is_valid()
True
>>> f.cleaned_data
{'field': u'1,,2'}
>>> f = CommaSeparatedIntegerForm({'field': '1'})
>>> f.is_valid()
True
>>> f.cleaned_data
{'field': u'1'}

This Price instance generated by this form is not valid because the quantity
field is required, but the form is valid because the field is excluded from
the form. This is for backwards compatibility.

>>> class PriceForm(ModelForm):
...     class Meta:
...         model = Price
...         exclude = ('quantity',)
>>> form = PriceForm({'price': '6.00'})
>>> form.is_valid()
True
>>> price = form.save(commit=False)
>>> price.full_clean()
Traceback (most recent call last):
  ...
ValidationError: {'quantity': [u'This field cannot be null.']}

The form should not validate fields that it doesn't contain even if they are
specified using 'fields', not 'exclude'.
...     class Meta:
...         model = Price
...         fields = ('price',)
>>> form = PriceForm({'price': '6.00'})
>>> form.is_valid()
True

The form should still have an instance of a model that is not complete and
not saved into a DB yet.

>>> form.instance.price
Decimal('6.00')
>>> form.instance.quantity is None
True
>>> form.instance.pk is None
True

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

>>> class CategoryForm(ModelForm):
...     description = forms.CharField()
...     class Meta:
...         model = Category
...         fields = ['description', 'url']

>>> CategoryForm.base_fields.keys()
['description', 'url']

>>> print CategoryForm()
<tr><th><label for="id_description">Description:</label></th><td><input type="text" name="description" id="id_description" /></td></tr>
<tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" /></td></tr>

# to_field_name should also work on ModelMultipleChoiceField ##################

>>> field = ModelMultipleChoiceField(Inventory.objects.all(), to_field_name='barcode')
>>> for choice in field.choices:
...     print choice
(86, u'Apple')
(22, u'Pear')
(87, u'Core')
>>> field.clean([86])
[<Inventory: Apple>]

>>> class SelectInventoryForm(forms.Form):
...     items = ModelMultipleChoiceField(Inventory.objects.all(), to_field_name='barcode')
>>> form = SelectInventoryForm({'items': [87, 22]})
>>> form.is_valid()
True
>>> form.cleaned_data
{'items': [<Inventory: Pear>, <Inventory: Core>]}

# Model field that returns None to exclude itself with explicit fields ########

>>> class CustomFieldForExclusionForm(ModelForm):
...     class Meta:
...         model = CustomFieldForExclusionModel
...         fields = ['name', 'markup']

>>> CustomFieldForExclusionForm.base_fields.keys()
['name']

>>> print CustomFieldForExclusionForm()
<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="10" /></td></tr>

# Clean up
>>> import shutil
>>> shutil.rmtree(temp_storage_dir)
"""


class ValidationTest(TestCase):
    def test_validates_with_replaced_field_not_specified(self):
        form = IncompleteCategoryFormWithFields(data={'name': 'some name', 'slug': 'some-slug'})
        assert form.is_valid()

    def test_validates_with_replaced_field_excluded(self):
        form = IncompleteCategoryFormWithExclude(data={'name': 'some name', 'slug': 'some-slug'})
        assert form.is_valid()

    def test_notrequired_overrides_notblank(self):
        form = CustomWriterForm({})
        assert form.is_valid()

# unique/unique_together validation
class UniqueTest(TestCase):
    def setUp(self):
        self.writer = Writer.objects.create(name='Mike Royko')

    def test_simple_unique(self):
        form = ProductForm({'slug': 'teddy-bear-blue'})
        self.assertTrue(form.is_valid())
        obj = form.save()
        form = ProductForm({'slug': 'teddy-bear-blue'})
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['slug'], [u'Product with this Slug already exists.'])
        form = ProductForm({'slug': 'teddy-bear-blue'}, instance=obj)
        self.assertTrue(form.is_valid())

    def test_unique_together(self):
        """ModelForm test of unique_together constraint"""
        form = PriceForm({'price': '6.00', 'quantity': '1'})
        self.assertTrue(form.is_valid())
        form.save()
        form = PriceForm({'price': '6.00', 'quantity': '1'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'], [u'Price with this Price and Quantity already exists.'])

    def test_unique_null(self):
        title = 'I May Be Wrong But I Doubt It'
        form = BookForm({'title': title, 'author': self.writer.pk})
        self.assertTrue(form.is_valid())
        form.save()
        form = BookForm({'title': title, 'author': self.writer.pk})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'], [u'Book with this Title and Author already exists.'])
        form = BookForm({'title': title})
        self.assertTrue(form.is_valid())
        form.save()
        form = BookForm({'title': title})
        self.assertTrue(form.is_valid())

    def test_inherited_unique(self):
        title = 'Boss'
        Book.objects.create(title=title, author=self.writer, special_id=1)
        form = DerivedBookForm({'title': 'Other', 'author': self.writer.pk, 'special_id': u'1', 'isbn': '12345'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['special_id'], [u'Book with this Special id already exists.'])

    def test_inherited_unique_together(self):
        title = 'Boss'
        form = BookForm({'title': title, 'author': self.writer.pk})
        self.assertTrue(form.is_valid())
        form.save()
        form = DerivedBookForm({'title': title, 'author': self.writer.pk, 'isbn': '12345'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'], [u'Book with this Title and Author already exists.'])

    def test_abstract_inherited_unique(self):
        title = 'Boss'
        isbn = '12345'
        dbook = DerivedBook.objects.create(title=title, author=self.writer, isbn=isbn)
        form = DerivedBookForm({'title': 'Other', 'author': self.writer.pk, 'isbn': isbn})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['isbn'], [u'Derived book with this Isbn already exists.'])

    def test_abstract_inherited_unique_together(self):
        title = 'Boss'
        isbn = '12345'
        dbook = DerivedBook.objects.create(title=title, author=self.writer, isbn=isbn)
        form = DerivedBookForm({'title': 'Other', 'author': self.writer.pk, 'isbn': '9876', 'suffix1': u'0', 'suffix2': u'0'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'], [u'Derived book with this Suffix1 and Suffix2 already exists.'])

    def test_explicitpk_unspecified(self):
        """Test for primary_key being in the form and failing validation."""
        form = ExplicitPKForm({'key': u'', 'desc': u'' })
        self.assertFalse(form.is_valid())

    def test_explicitpk_unique(self):
        """Ensure keys and blank character strings are tested for uniqueness."""
        form = ExplicitPKForm({'key': u'key1', 'desc': u''})
        self.assertTrue(form.is_valid())
        form.save()
        form = ExplicitPKForm({'key': u'key1', 'desc': u''})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 3)
        self.assertEqual(form.errors['__all__'], [u'Explicit pk with this Key and Desc already exists.'])
        self.assertEqual(form.errors['desc'], [u'Explicit pk with this Desc already exists.'])
        self.assertEqual(form.errors['key'], [u'Explicit pk with this Key already exists.'])

    def test_unique_for_date(self):
        p = Post.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))
        form = PostForm({'title': "Django 1.0 is released", 'posted': '2008-09-03'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['title'], [u'Title must be unique for Posted date.'])
        form = PostForm({'title': "Work on Django 1.1 begins", 'posted': '2008-09-03'})
        self.assertTrue(form.is_valid())
        form = PostForm({'title': "Django 1.0 is released", 'posted': '2008-09-04'})
        self.assertTrue(form.is_valid())
        form = PostForm({'slug': "Django 1.0", 'posted': '2008-01-01'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['slug'], [u'Slug must be unique for Posted year.'])
        form = PostForm({'subtitle': "Finally", 'posted': '2008-09-30'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['subtitle'], [u'Subtitle must be unique for Posted month.'])
        form = PostForm({'subtitle': "Finally", "title": "Django 1.0 is released",
            "slug": "Django 1.0", 'posted': '2008-09-03'}, instance=p)
        self.assertTrue(form.is_valid())
        form = PostForm({'title': "Django 1.0 is released"})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['posted'], [u'This field is required.'])

    def test_inherited_unique_for_date(self):
        p = Post.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))
        form = DerivedPostForm({'title': "Django 1.0 is released", 'posted': '2008-09-03'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['title'], [u'Title must be unique for Posted date.'])
        form = DerivedPostForm({'title': "Work on Django 1.1 begins", 'posted': '2008-09-03'})
        self.assertTrue(form.is_valid())
        form = DerivedPostForm({'title': "Django 1.0 is released", 'posted': '2008-09-04'})
        self.assertTrue(form.is_valid())
        form = DerivedPostForm({'slug': "Django 1.0", 'posted': '2008-01-01'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['slug'], [u'Slug must be unique for Posted year.'])
        form = DerivedPostForm({'subtitle': "Finally", 'posted': '2008-09-30'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['subtitle'], [u'Subtitle must be unique for Posted month.'])
        form = DerivedPostForm({'subtitle': "Finally", "title": "Django 1.0 is released",
            "slug": "Django 1.0", 'posted': '2008-09-03'}, instance=p)
        self.assertTrue(form.is_valid())

    def test_unique_for_date_with_nullable_date(self):
        p = FlexibleDatePost.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))

        form = FlexDatePostForm({'title': "Django 1.0 is released"})
        self.assertTrue(form.is_valid())
        form = FlexDatePostForm({'slug': "Django 1.0"})
        self.assertTrue(form.is_valid())
        form = FlexDatePostForm({'subtitle': "Finally"})
        self.assertTrue(form.is_valid())
        form = FlexDatePostForm({'subtitle': "Finally", "title": "Django 1.0 is released",
            "slug": "Django 1.0"}, instance=p)
        self.assertTrue(form.is_valid())
