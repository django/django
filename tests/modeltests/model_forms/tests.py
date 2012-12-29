from __future__ import absolute_import, unicode_literals

import datetime
import os
from decimal import Decimal

from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import ValidationError
from django.db import connection
from django.db.models.query import EmptyQuerySet
from django.forms.models import model_to_dict
from django.utils._os import upath
from django.utils.unittest import skipUnless
from django.test import TestCase
from django.utils import six

from .models import (Article, ArticleStatus, BetterWriter, BigInt, Book,
    Category, CommaSeparatedInteger, CustomFieldForExclusionModel, DerivedBook,
    DerivedPost, ExplicitPK, FlexibleDatePost, ImprovedArticle,
    ImprovedArticleWithParentLink, Inventory, Post, Price,
    Product, TextFile, Writer, WriterProfile, Colour, ColourfulItem,
    test_images)

if test_images:
    from .models import ImageFile, OptionalImageFile
    class ImageFileForm(forms.ModelForm):
        class Meta:
            model = ImageFile

    class OptionalImageFileForm(forms.ModelForm):
        class Meta:
            model = OptionalImageFile

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product


class PriceForm(forms.ModelForm):
    class Meta:
        model = Price


class BookForm(forms.ModelForm):
    class Meta:
       model = Book


class DerivedBookForm(forms.ModelForm):
    class Meta:
        model = DerivedBook


class ExplicitPKForm(forms.ModelForm):
    class Meta:
        model = ExplicitPK
        fields = ('key', 'desc',)


class PostForm(forms.ModelForm):
    class Meta:
        model = Post


class DerivedPostForm(forms.ModelForm):
    class Meta:
        model = DerivedPost


class CustomWriterForm(forms.ModelForm):
   name = forms.CharField(required=False)

   class Meta:
       model = Writer


class FlexDatePostForm(forms.ModelForm):
    class Meta:
        model = FlexibleDatePost


class BaseCategoryForm(forms.ModelForm):
    class Meta:
        model = Category


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article

class PartialArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ('headline','pub_date')

class RoykoForm(forms.ModelForm):
    class Meta:
        model = Writer

class TestArticleForm(forms.ModelForm):
    class Meta:
        model = Article

class PartialArticleFormWithSlug(forms.ModelForm):
    class Meta:
        model = Article
        fields=('headline', 'slug', 'pub_date')

class ArticleStatusForm(forms.ModelForm):
    class Meta:
        model = ArticleStatus

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory

class SelectInventoryForm(forms.Form):
    items = forms.ModelMultipleChoiceField(Inventory.objects.all(), to_field_name='barcode')

class CustomFieldForExclusionForm(forms.ModelForm):
    class Meta:
        model = CustomFieldForExclusionModel
        fields = ['name', 'markup']

class ShortCategory(forms.ModelForm):
    name = forms.CharField(max_length=5)
    slug = forms.CharField(max_length=5)
    url = forms.CharField(max_length=3)

class ImprovedArticleForm(forms.ModelForm):
    class Meta:
        model = ImprovedArticle

class ImprovedArticleWithParentLinkForm(forms.ModelForm):
    class Meta:
        model = ImprovedArticleWithParentLink

class BetterWriterForm(forms.ModelForm):
    class Meta:
        model = BetterWriter

class WriterProfileForm(forms.ModelForm):
    class Meta:
        model = WriterProfile

class TextFileForm(forms.ModelForm):
    class Meta:
        model = TextFile

class BigIntForm(forms.ModelForm):
    class Meta:
        model = BigInt

class ModelFormWithMedia(forms.ModelForm):
    class Media:
        js = ('/some/form/javascript',)
        css = {
            'all': ('/some/form/css',)
        }
    class Meta:
        model = TextFile

class CommaSeparatedIntegerForm(forms.ModelForm):
   class Meta:
       model = CommaSeparatedInteger

class PriceFormWithoutQuantity(forms.ModelForm):
    class Meta:
        model = Price
        exclude = ('quantity',)

class ColourfulItemForm(forms.ModelForm):
    class Meta:
        model = ColourfulItem


class ModelFormBaseTest(TestCase):
    def test_base_form(self):
        self.assertEqual(list(BaseCategoryForm.base_fields),
                         ['name', 'slug', 'url'])

    def test_extra_fields(self):
        class ExtraFields(BaseCategoryForm):
            some_extra_field = forms.BooleanField()

        self.assertEqual(list(ExtraFields.base_fields),
                         ['name', 'slug', 'url', 'some_extra_field'])

    def test_replace_field(self):
        class ReplaceField(forms.ModelForm):
            url = forms.BooleanField()

            class Meta:
                model = Category

        self.assertTrue(isinstance(ReplaceField.base_fields['url'],
                                     forms.fields.BooleanField))

    def test_override_field(self):
        class WriterForm(forms.ModelForm):
            book = forms.CharField(required=False)

            class Meta:
                model = Writer

        wf = WriterForm({'name': 'Richard Lockridge'})
        self.assertTrue(wf.is_valid())

    def test_limit_fields(self):
        class LimitFields(forms.ModelForm):
            class Meta:
                model = Category
                fields = ['url']

        self.assertEqual(list(LimitFields.base_fields),
                         ['url'])

    def test_exclude_fields(self):
        class ExcludeFields(forms.ModelForm):
            class Meta:
                model = Category
                exclude = ['url']

        self.assertEqual(list(ExcludeFields.base_fields),
                         ['name', 'slug'])

    def test_confused_form(self):
        class ConfusedForm(forms.ModelForm):
            """ Using 'fields' *and* 'exclude'. Not sure why you'd want to do
            this, but uh, "be liberal in what you accept" and all.
            """
            class Meta:
                model = Category
                fields = ['name', 'url']
                exclude = ['url']

        self.assertEqual(list(ConfusedForm.base_fields),
                         ['name'])

    def test_mixmodel_form(self):
        class MixModelForm(BaseCategoryForm):
            """ Don't allow more than one 'model' definition in the
            inheritance hierarchy.  Technically, it would generate a valid
            form, but the fact that the resulting save method won't deal with
            multiple objects is likely to trip up people not familiar with the
            mechanics.
            """
            class Meta:
                model = Article
            # MixModelForm is now an Article-related thing, because MixModelForm.Meta
            # overrides BaseCategoryForm.Meta.

        self.assertEqual(
            list(MixModelForm.base_fields),
            ['headline', 'slug', 'pub_date', 'writer', 'article', 'categories', 'status']
        )

    def test_article_form(self):
        self.assertEqual(
            list(ArticleForm.base_fields),
            ['headline', 'slug', 'pub_date', 'writer', 'article', 'categories', 'status']
        )

    def test_bad_form(self):
        #First class with a Meta class wins...
        class BadForm(ArticleForm, BaseCategoryForm):
            pass

        self.assertEqual(
            list(BadForm.base_fields),
            ['headline', 'slug', 'pub_date', 'writer', 'article', 'categories', 'status']
        )

    def test_subcategory_form(self):
        class SubCategoryForm(BaseCategoryForm):
            """ Subclassing without specifying a Meta on the class will use
            the parent's Meta (or the first parent in the MRO if there are
            multiple parent classes).
            """
            pass

        self.assertEqual(list(SubCategoryForm.base_fields),
                         ['name', 'slug', 'url'])

    def test_subclassmeta_form(self):
        class SomeCategoryForm(forms.ModelForm):
             checkbox = forms.BooleanField()

             class Meta:
                 model = Category

        class SubclassMeta(SomeCategoryForm):
            """ We can also subclass the Meta inner class to change the fields
            list.
            """
            class Meta(SomeCategoryForm.Meta):
                exclude = ['url']

        self.assertHTMLEqual(
            str(SubclassMeta()),
            """<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" /></td></tr>
<tr><th><label for="id_slug">Slug:</label></th><td><input id="id_slug" type="text" name="slug" maxlength="20" /></td></tr>
<tr><th><label for="id_checkbox">Checkbox:</label></th><td><input type="checkbox" name="checkbox" id="id_checkbox" /></td></tr>"""
            )

    def test_orderfields_form(self):
        class OrderFields(forms.ModelForm):
            class Meta:
                model = Category
                fields = ['url', 'name']

        self.assertEqual(list(OrderFields.base_fields),
                         ['url', 'name'])
        self.assertHTMLEqual(
            str(OrderFields()),
            """<tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" /></td></tr>
<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" /></td></tr>"""
            )

    def test_orderfields2_form(self):
        class OrderFields2(forms.ModelForm):
            class Meta:
                model = Category
                fields = ['slug', 'url', 'name']
                exclude = ['url']

        self.assertEqual(list(OrderFields2.base_fields),
                         ['slug', 'name'])


class TestWidgetForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'url', 'slug']
        widgets = {
            'name': forms.Textarea,
            'url': forms.TextInput(attrs={'class': 'url'})
        }



class TestWidgets(TestCase):
    def test_base_widgets(self):
        frm = TestWidgetForm()
        self.assertHTMLEqual(
            str(frm['name']),
            '<textarea id="id_name" rows="10" cols="40" name="name"></textarea>'
        )
        self.assertHTMLEqual(
            str(frm['url']),
            '<input id="id_url" type="text" class="url" name="url" maxlength="40" />'
        )
        self.assertHTMLEqual(
            str(frm['slug']),
            '<input id="id_slug" type="text" name="slug" maxlength="20" />'
        )


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
        self.assertEqual(form.errors['slug'], ['Product with this Slug already exists.'])
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
        self.assertEqual(form.errors['__all__'], ['Price with this Price and Quantity already exists.'])

    def test_unique_null(self):
        title = 'I May Be Wrong But I Doubt It'
        form = BookForm({'title': title, 'author': self.writer.pk})
        self.assertTrue(form.is_valid())
        form.save()
        form = BookForm({'title': title, 'author': self.writer.pk})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'], ['Book with this Title and Author already exists.'])
        form = BookForm({'title': title})
        self.assertTrue(form.is_valid())
        form.save()
        form = BookForm({'title': title})
        self.assertTrue(form.is_valid())

    def test_inherited_unique(self):
        title = 'Boss'
        Book.objects.create(title=title, author=self.writer, special_id=1)
        form = DerivedBookForm({'title': 'Other', 'author': self.writer.pk, 'special_id': '1', 'isbn': '12345'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['special_id'], ['Book with this Special id already exists.'])

    def test_inherited_unique_together(self):
        title = 'Boss'
        form = BookForm({'title': title, 'author': self.writer.pk})
        self.assertTrue(form.is_valid())
        form.save()
        form = DerivedBookForm({'title': title, 'author': self.writer.pk, 'isbn': '12345'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'], ['Book with this Title and Author already exists.'])

    def test_abstract_inherited_unique(self):
        title = 'Boss'
        isbn = '12345'
        dbook = DerivedBook.objects.create(title=title, author=self.writer, isbn=isbn)
        form = DerivedBookForm({'title': 'Other', 'author': self.writer.pk, 'isbn': isbn})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['isbn'], ['Derived book with this Isbn already exists.'])

    def test_abstract_inherited_unique_together(self):
        title = 'Boss'
        isbn = '12345'
        dbook = DerivedBook.objects.create(title=title, author=self.writer, isbn=isbn)
        form = DerivedBookForm({
                    'title': 'Other',
                    'author': self.writer.pk,
                    'isbn': '9876',
                    'suffix1': '0',
                    'suffix2': '0'
                })
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['__all__'],
                         ['Derived book with this Suffix1 and Suffix2 already exists.'])

    def test_explicitpk_unspecified(self):
        """Test for primary_key being in the form and failing validation."""
        form = ExplicitPKForm({'key': '', 'desc': '' })
        self.assertFalse(form.is_valid())

    def test_explicitpk_unique(self):
        """Ensure keys and blank character strings are tested for uniqueness."""
        form = ExplicitPKForm({'key': 'key1', 'desc': ''})
        self.assertTrue(form.is_valid())
        form.save()
        form = ExplicitPKForm({'key': 'key1', 'desc': ''})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 3)
        self.assertEqual(form.errors['__all__'], ['Explicit pk with this Key and Desc already exists.'])
        self.assertEqual(form.errors['desc'], ['Explicit pk with this Desc already exists.'])
        self.assertEqual(form.errors['key'], ['Explicit pk with this Key already exists.'])

    def test_unique_for_date(self):
        p = Post.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))
        form = PostForm({'title': "Django 1.0 is released", 'posted': '2008-09-03'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['title'], ['Title must be unique for Posted date.'])
        form = PostForm({'title': "Work on Django 1.1 begins", 'posted': '2008-09-03'})
        self.assertTrue(form.is_valid())
        form = PostForm({'title': "Django 1.0 is released", 'posted': '2008-09-04'})
        self.assertTrue(form.is_valid())
        form = PostForm({'slug': "Django 1.0", 'posted': '2008-01-01'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['slug'], ['Slug must be unique for Posted year.'])
        form = PostForm({'subtitle': "Finally", 'posted': '2008-09-30'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['subtitle'], ['Subtitle must be unique for Posted month.'])
        form = PostForm({'subtitle': "Finally", "title": "Django 1.0 is released",
            "slug": "Django 1.0", 'posted': '2008-09-03'}, instance=p)
        self.assertTrue(form.is_valid())
        form = PostForm({'title': "Django 1.0 is released"})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['posted'], ['This field is required.'])

    def test_inherited_unique_for_date(self):
        p = Post.objects.create(title="Django 1.0 is released",
            slug="Django 1.0", subtitle="Finally", posted=datetime.date(2008, 9, 3))
        form = DerivedPostForm({'title': "Django 1.0 is released", 'posted': '2008-09-03'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['title'], ['Title must be unique for Posted date.'])
        form = DerivedPostForm({'title': "Work on Django 1.1 begins", 'posted': '2008-09-03'})
        self.assertTrue(form.is_valid())
        form = DerivedPostForm({'title': "Django 1.0 is released", 'posted': '2008-09-04'})
        self.assertTrue(form.is_valid())
        form = DerivedPostForm({'slug': "Django 1.0", 'posted': '2008-01-01'})
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertEqual(form.errors['slug'], ['Slug must be unique for Posted year.'])
        form = DerivedPostForm({'subtitle': "Finally", 'posted': '2008-09-30'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['subtitle'], ['Subtitle must be unique for Posted month.'])
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

class ModelToDictTests(TestCase):
    """
    Tests for forms.models.model_to_dict
    """
    def test_model_to_dict_many_to_many(self):
        categories=[
            Category(name='TestName1', slug='TestName1', url='url1'),
            Category(name='TestName2', slug='TestName2', url='url2'),
            Category(name='TestName3', slug='TestName3', url='url3')
        ]
        for c in categories:
            c.save()
        writer = Writer(name='Test writer')
        writer.save()

        art = Article(
            headline='Test article',
            slug='test-article',
            pub_date=datetime.date(1988, 1, 4),
            writer=writer,
            article='Hello.'
        )
        art.save()
        for c in categories:
            art.categories.add(c)
        art.save()

        with self.assertNumQueries(1):
            d = model_to_dict(art)

        #Ensure all many-to-many categories appear in model_to_dict
        for c in categories:
            self.assertIn(c.pk, d['categories'])
        #Ensure many-to-many relation appears as a list
        self.assertIsInstance(d['categories'], list)

class OldFormForXTests(TestCase):
    def test_base_form(self):
        self.assertEqual(Category.objects.count(), 0)
        f = BaseCategoryForm()
        self.assertHTMLEqual(
            str(f),
            """<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="20" /></td></tr>
<tr><th><label for="id_slug">Slug:</label></th><td><input id="id_slug" type="text" name="slug" maxlength="20" /></td></tr>
<tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" /></td></tr>"""
            )
        self.assertHTMLEqual(
            str(f.as_ul()),
            """<li><label for="id_name">Name:</label> <input id="id_name" type="text" name="name" maxlength="20" /></li>
<li><label for="id_slug">Slug:</label> <input id="id_slug" type="text" name="slug" maxlength="20" /></li>
<li><label for="id_url">The URL:</label> <input id="id_url" type="text" name="url" maxlength="40" /></li>"""
            )
        self.assertHTMLEqual(
            str(f["name"]),
            """<input id="id_name" type="text" name="name" maxlength="20" />""")

    def test_auto_id(self):
        f = BaseCategoryForm(auto_id=False)
        self.assertHTMLEqual(
            str(f.as_ul()),
            """<li>Name: <input type="text" name="name" maxlength="20" /></li>
<li>Slug: <input type="text" name="slug" maxlength="20" /></li>
<li>The URL: <input type="text" name="url" maxlength="40" /></li>"""
            )

    def test_with_data(self):
        self.assertEqual(Category.objects.count(), 0)
        f = BaseCategoryForm({'name': 'Entertainment',
                              'slug': 'entertainment',
                              'url': 'entertainment'})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data['name'], 'Entertainment')
        self.assertEqual(f.cleaned_data['slug'], 'entertainment')
        self.assertEqual(f.cleaned_data['url'], 'entertainment')
        c1 = f.save()
        # Testing wether the same object is returned from the
        # ORM... not the fastest way...

        self.assertEqual(c1, Category.objects.all()[0])
        self.assertEqual(c1.name, "Entertainment")
        self.assertEqual(Category.objects.count(), 1)

        f = BaseCategoryForm({'name': "It's a test",
                              'slug': 'its-test',
                              'url': 'test'})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data['name'], "It's a test")
        self.assertEqual(f.cleaned_data['slug'], 'its-test')
        self.assertEqual(f.cleaned_data['url'], 'test')
        c2 = f.save()
        # Testing wether the same object is returned from the
        # ORM... not the fastest way...
        self.assertEqual(c2, Category.objects.get(pk=c2.pk))
        self.assertEqual(c2.name, "It's a test")
        self.assertEqual(Category.objects.count(), 2)

        # If you call save() with commit=False, then it will return an object that
        # hasn't yet been saved to the database. In this case, it's up to you to call
        # save() on the resulting model instance.
        f = BaseCategoryForm({'name': 'Third test', 'slug': 'third-test', 'url': 'third'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['url'], 'third')
        self.assertEqual(f.cleaned_data['name'], 'Third test')
        self.assertEqual(f.cleaned_data['slug'], 'third-test')
        c3 = f.save(commit=False)
        self.assertEqual(c3.name, "Third test")
        self.assertEqual(Category.objects.count(), 2)
        c3.save()
        self.assertEqual(Category.objects.count(), 3)

        # If you call save() with invalid data, you'll get a ValueError.
        f = BaseCategoryForm({'name': '', 'slug': 'not a slug!', 'url': 'foo'})
        self.assertEqual(f.errors['name'], ['This field is required.'])
        self.assertEqual(f.errors['slug'], ["Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens."])
        self.assertEqual(f.cleaned_data, {'url': 'foo'})
        with self.assertRaises(ValueError):
            f.save()
        f = BaseCategoryForm({'name': '', 'slug': '', 'url': 'foo'})
        with self.assertRaises(ValueError):
            f.save()

        # Create a couple of Writers.
        w_royko = Writer(name='Mike Royko')
        w_royko.save()
        w_woodward = Writer(name='Bob Woodward')
        w_woodward.save()
        # ManyToManyFields are represented by a MultipleChoiceField, ForeignKeys and any
        # fields with the 'choices' attribute are represented by a ChoiceField.
        f = ArticleForm(auto_id=False)
        self.assertHTMLEqual(six.text_type(f), '''<tr><th>Headline:</th><td><input type="text" name="headline" maxlength="50" /></td></tr>
<tr><th>Slug:</th><td><input type="text" name="slug" maxlength="50" /></td></tr>
<tr><th>Pub date:</th><td><input type="text" name="pub_date" /></td></tr>
<tr><th>Writer:</th><td><select name="writer">
<option value="" selected="selected">---------</option>
<option value="%s">Bob Woodward</option>
<option value="%s">Mike Royko</option>
</select></td></tr>
<tr><th>Article:</th><td><textarea rows="10" cols="40" name="article"></textarea></td></tr>
<tr><th>Categories:</th><td><select multiple="multiple" name="categories">
<option value="%s">Entertainment</option>
<option value="%s">It&#39;s a test</option>
<option value="%s">Third test</option>
</select><br /><span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></td></tr>
<tr><th>Status:</th><td><select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></td></tr>''' % (w_woodward.pk, w_royko.pk, c1.pk, c2.pk, c3.pk))

        # You can restrict a form to a subset of the complete list of fields
        # by providing a 'fields' argument. If you try to save a
        # model created with such a form, you need to ensure that the fields
        # that are _not_ on the form have default values, or are allowed to have
        # a value of None. If a field isn't specified on a form, the object created
        # from the form can't provide a value for that field!
        f = PartialArticleForm(auto_id=False)
        self.assertHTMLEqual(six.text_type(f), '''<tr><th>Headline:</th><td><input type="text" name="headline" maxlength="50" /></td></tr>
<tr><th>Pub date:</th><td><input type="text" name="pub_date" /></td></tr>''')

        # When the ModelForm is passed an instance, that instance's current values are
        # inserted as 'initial' data in each Field.
        w = Writer.objects.get(name='Mike Royko')
        f = RoykoForm(auto_id=False, instance=w)
        self.assertHTMLEqual(six.text_type(f), '''<tr><th>Name:</th><td><input type="text" name="name" value="Mike Royko" maxlength="50" /><br /><span class="helptext">Use both first and last names.</span></td></tr>''')

        art = Article(
                    headline='Test article',
                    slug='test-article',
                    pub_date=datetime.date(1988, 1, 4),
                    writer=w,
                    article='Hello.'
                )
        art.save()
        art_id_1 = art.id
        self.assertEqual(art_id_1 is not None, True)
        f = TestArticleForm(auto_id=False, instance=art)
        self.assertHTMLEqual(f.as_ul(), '''<li>Headline: <input type="text" name="headline" value="Test article" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" value="test-article" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>
<li>Writer: <select name="writer">
<option value="">---------</option>
<option value="%s">Bob Woodward</option>
<option value="%s" selected="selected">Mike Royko</option>
</select></li>
<li>Article: <textarea rows="10" cols="40" name="article">Hello.</textarea></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="%s">Entertainment</option>
<option value="%s">It&#39;s a test</option>
<option value="%s">Third test</option>
</select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
<li>Status: <select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></li>''' % (w_woodward.pk, w_royko.pk, c1.pk, c2.pk, c3.pk))
        f = TestArticleForm({
                'headline': 'Test headline',
                'slug': 'test-headline',
                'pub_date': '1984-02-06',
                'writer': six.text_type(w_royko.pk),
                'article': 'Hello.'
            }, instance=art)
        self.assertEqual(f.errors, {})
        self.assertEqual(f.is_valid(), True)
        test_art = f.save()
        self.assertEqual(test_art.id == art_id_1, True)
        test_art = Article.objects.get(id=art_id_1)
        self.assertEqual(test_art.headline, 'Test headline')
        # You can create a form over a subset of the available fields
        # by specifying a 'fields' argument to form_for_instance.
        f = PartialArticleFormWithSlug({
                'headline': 'New headline',
                'slug': 'new-headline',
                'pub_date': '1988-01-04'
            }, auto_id=False, instance=art)
        self.assertHTMLEqual(f.as_ul(), '''<li>Headline: <input type="text" name="headline" value="New headline" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" value="new-headline" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>''')
        self.assertEqual(f.is_valid(), True)
        new_art = f.save()
        self.assertEqual(new_art.id == art_id_1, True)
        new_art = Article.objects.get(id=art_id_1)
        self.assertEqual(new_art.headline, 'New headline')

        # Add some categories and test the many-to-many form output.
        self.assertQuerysetEqual(new_art.categories.all(), [])
        new_art.categories.add(Category.objects.get(name='Entertainment'))
        self.assertQuerysetEqual(new_art.categories.all(), ["Entertainment"])
        f = TestArticleForm(auto_id=False, instance=new_art)
        self.assertHTMLEqual(f.as_ul(), '''<li>Headline: <input type="text" name="headline" value="New headline" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" value="new-headline" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" value="1988-01-04" /></li>
<li>Writer: <select name="writer">
<option value="">---------</option>
<option value="%s">Bob Woodward</option>
<option value="%s" selected="selected">Mike Royko</option>
</select></li>
<li>Article: <textarea rows="10" cols="40" name="article">Hello.</textarea></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="%s" selected="selected">Entertainment</option>
<option value="%s">It&#39;s a test</option>
<option value="%s">Third test</option>
</select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
<li>Status: <select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></li>''' % (w_woodward.pk, w_royko.pk, c1.pk, c2.pk, c3.pk))

        # Initial values can be provided for model forms
        f = TestArticleForm(
                auto_id=False,
                initial={
                    'headline': 'Your headline here',
                    'categories': [str(c1.id), str(c2.id)]
                })
        self.assertHTMLEqual(f.as_ul(), '''<li>Headline: <input type="text" name="headline" value="Your headline here" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" /></li>
<li>Writer: <select name="writer">
<option value="" selected="selected">---------</option>
<option value="%s">Bob Woodward</option>
<option value="%s">Mike Royko</option>
</select></li>
<li>Article: <textarea rows="10" cols="40" name="article"></textarea></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="%s" selected="selected">Entertainment</option>
<option value="%s" selected="selected">It&#39;s a test</option>
<option value="%s">Third test</option>
</select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
<li>Status: <select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></li>''' % (w_woodward.pk, w_royko.pk, c1.pk, c2.pk, c3.pk))

        f = TestArticleForm({
                'headline': 'New headline',
                'slug': 'new-headline',
                'pub_date': '1988-01-04',
                'writer': six.text_type(w_royko.pk),
                'article': 'Hello.',
                'categories': [six.text_type(c1.id), six.text_type(c2.id)]
            }, instance=new_art)
        new_art = f.save()
        self.assertEqual(new_art.id == art_id_1, True)
        new_art = Article.objects.get(id=art_id_1)
        self.assertQuerysetEqual(new_art.categories.order_by('name'),
                         ["Entertainment", "It's a test"])

        # Now, submit form data with no categories. This deletes the existing categories.
        f = TestArticleForm({'headline': 'New headline', 'slug': 'new-headline', 'pub_date': '1988-01-04',
            'writer': six.text_type(w_royko.pk), 'article': 'Hello.'}, instance=new_art)
        new_art = f.save()
        self.assertEqual(new_art.id == art_id_1, True)
        new_art = Article.objects.get(id=art_id_1)
        self.assertQuerysetEqual(new_art.categories.all(), [])

        # Create a new article, with categories, via the form.
        f = ArticleForm({'headline': 'The walrus was Paul', 'slug': 'walrus-was-paul', 'pub_date': '1967-11-01',
            'writer': six.text_type(w_royko.pk), 'article': 'Test.', 'categories': [six.text_type(c1.id), six.text_type(c2.id)]})
        new_art = f.save()
        art_id_2 = new_art.id
        self.assertEqual(art_id_2 not in (None, art_id_1), True)
        new_art = Article.objects.get(id=art_id_2)
        self.assertQuerysetEqual(new_art.categories.order_by('name'), ["Entertainment", "It's a test"])

        # Create a new article, with no categories, via the form.
        f = ArticleForm({'headline': 'The walrus was Paul', 'slug': 'walrus-was-paul', 'pub_date': '1967-11-01',
            'writer': six.text_type(w_royko.pk), 'article': 'Test.'})
        new_art = f.save()
        art_id_3 = new_art.id
        self.assertEqual(art_id_3 not in (None, art_id_1, art_id_2), True)
        new_art = Article.objects.get(id=art_id_3)
        self.assertQuerysetEqual(new_art.categories.all(), [])

        # Create a new article, with categories, via the form, but use commit=False.
        # The m2m data won't be saved until save_m2m() is invoked on the form.
        f = ArticleForm({'headline': 'The walrus was Paul', 'slug': 'walrus-was-paul', 'pub_date': '1967-11-01',
            'writer': six.text_type(w_royko.pk), 'article': 'Test.', 'categories': [six.text_type(c1.id), six.text_type(c2.id)]})
        new_art = f.save(commit=False)

        # Manually save the instance
        new_art.save()
        art_id_4 = new_art.id
        self.assertEqual(art_id_4 not in (None, art_id_1, art_id_2, art_id_3), True)

        # The instance doesn't have m2m data yet
        new_art = Article.objects.get(id=art_id_4)
        self.assertQuerysetEqual(new_art.categories.all(), [])

        # Save the m2m data on the form
        f.save_m2m()
        self.assertQuerysetEqual(new_art.categories.order_by('name'), ["Entertainment", "It's a test"])

        # Here, we define a custom ModelForm. Because it happens to have the same fields as
        # the Category model, we can just call the form's save() to apply its changes to an
        # existing Category instance.
        cat = Category.objects.get(name='Third test')
        self.assertEqual(cat.name, "Third test")
        self.assertEqual(cat.id == c3.id, True)
        form = ShortCategory({'name': 'Third', 'slug': 'third', 'url': '3rd'}, instance=cat)
        self.assertEqual(form.save().name, 'Third')
        self.assertEqual(Category.objects.get(id=c3.id).name, 'Third')

        # Here, we demonstrate that choices for a ForeignKey ChoiceField are determined
        # at runtime, based on the data in the database when the form is displayed, not
        # the data in the database when the form is instantiated.
        f = ArticleForm(auto_id=False)
        self.assertHTMLEqual(f.as_ul(), '''<li>Headline: <input type="text" name="headline" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" /></li>
<li>Writer: <select name="writer">
<option value="" selected="selected">---------</option>
<option value="%s">Bob Woodward</option>
<option value="%s">Mike Royko</option>
</select></li>
<li>Article: <textarea rows="10" cols="40" name="article"></textarea></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="%s">Entertainment</option>
<option value="%s">It&#39;s a test</option>
<option value="%s">Third</option>
</select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
<li>Status: <select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></li>''' % (w_woodward.pk, w_royko.pk, c1.pk, c2.pk, c3.pk))

        c4 = Category.objects.create(name='Fourth', url='4th')
        self.assertEqual(c4.name, 'Fourth')
        w_bernstein = Writer.objects.create(name='Carl Bernstein')
        self.assertEqual(w_bernstein.name, 'Carl Bernstein')
        self.assertHTMLEqual(f.as_ul(), '''<li>Headline: <input type="text" name="headline" maxlength="50" /></li>
<li>Slug: <input type="text" name="slug" maxlength="50" /></li>
<li>Pub date: <input type="text" name="pub_date" /></li>
<li>Writer: <select name="writer">
<option value="" selected="selected">---------</option>
<option value="%s">Bob Woodward</option>
<option value="%s">Carl Bernstein</option>
<option value="%s">Mike Royko</option>
</select></li>
<li>Article: <textarea rows="10" cols="40" name="article"></textarea></li>
<li>Categories: <select multiple="multiple" name="categories">
<option value="%s">Entertainment</option>
<option value="%s">It&#39;s a test</option>
<option value="%s">Third</option>
<option value="%s">Fourth</option>
</select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></li>
<li>Status: <select name="status">
<option value="" selected="selected">---------</option>
<option value="1">Draft</option>
<option value="2">Pending</option>
<option value="3">Live</option>
</select></li>''' % (w_woodward.pk, w_bernstein.pk, w_royko.pk, c1.pk, c2.pk, c3.pk, c4.pk))

        # ModelChoiceField ############################################################

        f = forms.ModelChoiceField(Category.objects.all())
        self.assertEqual(list(f.choices), [
            ('', '---------'),
            (c1.pk, 'Entertainment'),
            (c2.pk, "It's a test"),
            (c3.pk, 'Third'),
            (c4.pk, 'Fourth')])
        with self.assertRaises(ValidationError):
            f.clean('')
        with self.assertRaises(ValidationError):
            f.clean(None)
        with self.assertRaises(ValidationError):
            f.clean(0)
        self.assertEqual(f.clean(c3.id).name, 'Third')
        self.assertEqual(f.clean(c2.id).name, "It's a test")

        # Add a Category object *after* the ModelChoiceField has already been
        # instantiated. This proves clean() checks the database during clean() rather
        # than caching it at time of instantiation.
        c5 = Category.objects.create(name='Fifth', url='5th')
        self.assertEqual(c5.name, 'Fifth')
        self.assertEqual(f.clean(c5.id).name, 'Fifth')

        # Delete a Category object *after* the ModelChoiceField has already been
        # instantiated. This proves clean() checks the database during clean() rather
        # than caching it at time of instantiation.
        Category.objects.get(url='5th').delete()
        with self.assertRaises(ValidationError):
            f.clean(c5.id)

        f = forms.ModelChoiceField(Category.objects.filter(pk=c1.id), required=False)
        self.assertEqual(f.clean(''), None)
        f.clean('')
        self.assertEqual(f.clean(str(c1.id)).name, "Entertainment")
        with self.assertRaises(ValidationError):
            f.clean('100')

        # queryset can be changed after the field is created.
        f.queryset = Category.objects.exclude(name='Fourth')
        self.assertEqual(list(f.choices), [
            ('', '---------'),
            (c1.pk, 'Entertainment'),
            (c2.pk, "It's a test"),
            (c3.pk, 'Third')])
        self.assertEqual(f.clean(c3.id).name, 'Third')
        with self.assertRaises(ValidationError):
            f.clean(c4.id)

        # check that we can safely iterate choices repeatedly
        gen_one = list(f.choices)
        gen_two = f.choices
        self.assertEqual(gen_one[2], (c2.pk, "It's a test"))
        self.assertEqual(list(gen_two), [
            ('', '---------'),
            (c1.pk, 'Entertainment'),
            (c2.pk, "It's a test"),
            (c3.pk, 'Third')])

        # check that we can override the label_from_instance method to print custom labels (#4620)
        f.queryset = Category.objects.all()
        f.label_from_instance = lambda obj: "category " + str(obj)
        self.assertEqual(list(f.choices), [
            ('', '---------'),
            (c1.pk, 'category Entertainment'),
            (c2.pk, "category It's a test"),
            (c3.pk, 'category Third'),
            (c4.pk, 'category Fourth')])

        # ModelMultipleChoiceField ####################################################

        f = forms.ModelMultipleChoiceField(Category.objects.all())
        self.assertEqual(list(f.choices), [
            (c1.pk, 'Entertainment'),
            (c2.pk, "It's a test"),
            (c3.pk, 'Third'),
            (c4.pk, 'Fourth')])
        with self.assertRaises(ValidationError):
            f.clean(None)
        with self.assertRaises(ValidationError):
            f.clean([])
        self.assertQuerysetEqual(f.clean([c1.id]), ["Entertainment"])
        self.assertQuerysetEqual(f.clean([c2.id]), ["It's a test"])
        self.assertQuerysetEqual(f.clean([str(c1.id)]), ["Entertainment"])
        self.assertQuerysetEqual(f.clean([str(c1.id), str(c2.id)]), ["Entertainment", "It's a test"],
                                 ordered=False)
        self.assertQuerysetEqual(f.clean([c1.id, str(c2.id)]), ["Entertainment", "It's a test"],
                                 ordered=False)
        self.assertQuerysetEqual(f.clean((c1.id, str(c2.id))), ["Entertainment", "It's a test"],
                                 ordered=False)
        with self.assertRaises(ValidationError):
            f.clean(['100'])
        with self.assertRaises(ValidationError):
            f.clean('hello')
        with self.assertRaises(ValidationError):
            f.clean(['fail'])

        # Add a Category object *after* the ModelMultipleChoiceField has already been
        # instantiated. This proves clean() checks the database during clean() rather
        # than caching it at time of instantiation.
        # Note, we are using an id of 1006 here since tests that run before
        # this may create categories with primary keys up to 6. Use
        # a number that is will not conflict.
        c6 = Category.objects.create(id=1006, name='Sixth', url='6th')
        self.assertEqual(c6.name, 'Sixth')
        self.assertQuerysetEqual(f.clean([c6.id]), ["Sixth"])

        # Delete a Category object *after* the ModelMultipleChoiceField has already been
        # instantiated. This proves clean() checks the database during clean() rather
        # than caching it at time of instantiation.
        Category.objects.get(url='6th').delete()
        with self.assertRaises(ValidationError):
            f.clean([c6.id])

        f = forms.ModelMultipleChoiceField(Category.objects.all(), required=False)
        self.assertIsInstance(f.clean([]), EmptyQuerySet)
        self.assertIsInstance(f.clean(()), EmptyQuerySet)
        with self.assertRaises(ValidationError):
            f.clean(['10'])
        with self.assertRaises(ValidationError):
            f.clean([str(c3.id), '10'])
        with self.assertRaises(ValidationError):
            f.clean([str(c1.id), '10'])

        # queryset can be changed after the field is created.
        f.queryset = Category.objects.exclude(name='Fourth')
        self.assertEqual(list(f.choices), [
            (c1.pk, 'Entertainment'),
            (c2.pk, "It's a test"),
            (c3.pk, 'Third')])
        self.assertQuerysetEqual(f.clean([c3.id]), ["Third"])
        with self.assertRaises(ValidationError):
            f.clean([c4.id])
        with self.assertRaises(ValidationError):
            f.clean([str(c3.id), str(c4.id)])

        f.queryset = Category.objects.all()
        f.label_from_instance = lambda obj: "multicategory " + str(obj)
        self.assertEqual(list(f.choices), [
            (c1.pk, 'multicategory Entertainment'),
            (c2.pk, "multicategory It's a test"),
            (c3.pk, 'multicategory Third'),
            (c4.pk, 'multicategory Fourth')])

        # OneToOneField ###############################################################

        self.assertEqual(list(ImprovedArticleForm.base_fields), ['article'])

        self.assertEqual(list(ImprovedArticleWithParentLinkForm.base_fields), [])

        bw = BetterWriter(name='Joe Better', score=10)
        bw.save()
        self.assertEqual(sorted(model_to_dict(bw)),
                         ['id', 'name', 'score', 'writer_ptr'])

        form = BetterWriterForm({'name': 'Some Name', 'score': 12})
        self.assertEqual(form.is_valid(), True)
        bw2 = form.save()
        bw2.delete()

        form = WriterProfileForm()
        self.assertHTMLEqual(form.as_p(), '''<p><label for="id_writer">Writer:</label> <select name="writer" id="id_writer">
<option value="" selected="selected">---------</option>
<option value="%s">Bob Woodward</option>
<option value="%s">Carl Bernstein</option>
<option value="%s">Joe Better</option>
<option value="%s">Mike Royko</option>
</select></p>
<p><label for="id_age">Age:</label> <input type="text" name="age" id="id_age" /></p>''' % (w_woodward.pk, w_bernstein.pk, bw.pk, w_royko.pk))

        data = {
            'writer': six.text_type(w_woodward.pk),
            'age': '65',
        }
        form = WriterProfileForm(data)
        instance = form.save()
        self.assertEqual(six.text_type(instance), 'Bob Woodward is 65')

        form = WriterProfileForm(instance=instance)
        self.assertHTMLEqual(form.as_p(), '''<p><label for="id_writer">Writer:</label> <select name="writer" id="id_writer">
<option value="">---------</option>
<option value="%s" selected="selected">Bob Woodward</option>
<option value="%s">Carl Bernstein</option>
<option value="%s">Joe Better</option>
<option value="%s">Mike Royko</option>
</select></p>
<p><label for="id_age">Age:</label> <input type="text" name="age" value="65" id="id_age" /></p>''' % (w_woodward.pk, w_bernstein.pk, bw.pk, w_royko.pk))

    def test_file_field(self):
        # Test conditions when files is either not given or empty.

        f = TextFileForm(data={'description': 'Assistance'})
        self.assertEqual(f.is_valid(), False)
        f = TextFileForm(data={'description': 'Assistance'}, files={})
        self.assertEqual(f.is_valid(), False)

        # Upload a file and ensure it all works as expected.

        f = TextFileForm(
                data={'description': 'Assistance'},
                files={'file': SimpleUploadedFile('test1.txt', b'hello world')})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(type(f.cleaned_data['file']), SimpleUploadedFile)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test1.txt')

        instance.file.delete()
        f = TextFileForm(
                data={'description': 'Assistance'},
                files={'file': SimpleUploadedFile('test1.txt', b'hello world')})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(type(f.cleaned_data['file']), SimpleUploadedFile)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test1.txt')

        # Check if the max_length attribute has been inherited from the model.
        f = TextFileForm(
                data={'description': 'Assistance'},
                files={'file': SimpleUploadedFile('test-maxlength.txt', b'hello world')})
        self.assertEqual(f.is_valid(), False)

        # Edit an instance that already has the file defined in the model. This will not
        # save the file again, but leave it exactly as it is.

        f = TextFileForm(
                data={'description': 'Assistance'},
                instance=instance)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['file'].name, 'tests/test1.txt')
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test1.txt')

        # Delete the current file since this is not done by Django.
        instance.file.delete()

        # Override the file by uploading a new one.

        f = TextFileForm(
                data={'description': 'Assistance'},
                files={'file': SimpleUploadedFile('test2.txt', b'hello world')}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test2.txt')

        # Delete the current file since this is not done by Django.
        instance.file.delete()
        f = TextFileForm(
                data={'description': 'Assistance'},
                files={'file': SimpleUploadedFile('test2.txt', b'hello world')})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test2.txt')

        # Delete the current file since this is not done by Django.
        instance.file.delete()

        instance.delete()

        # Test the non-required FileField
        f = TextFileForm(data={'description': 'Assistance'})
        f.fields['file'].required = False
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.file.name, '')

        f = TextFileForm(
                data={'description': 'Assistance'},
                files={'file': SimpleUploadedFile('test3.txt', b'hello world')}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test3.txt')

        # Instance can be edited w/out re-uploading the file and existing file should be preserved.

        f = TextFileForm(
                data={'description': 'New Description'},
                instance=instance)
        f.fields['file'].required = False
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.description, 'New Description')
        self.assertEqual(instance.file.name, 'tests/test3.txt')

        # Delete the current file since this is not done by Django.
        instance.file.delete()
        instance.delete()

        f = TextFileForm(
                data={'description': 'Assistance'},
                files={'file': SimpleUploadedFile('test3.txt', b'hello world')})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.file.name, 'tests/test3.txt')

        # Delete the current file since this is not done by Django.
        instance.file.delete()
        instance.delete()

    def test_big_integer_field(self):
        bif = BigIntForm({'biggie': '-9223372036854775808'})
        self.assertEqual(bif.is_valid(), True)
        bif = BigIntForm({'biggie': '-9223372036854775809'})
        self.assertEqual(bif.is_valid(), False)
        self.assertEqual(bif.errors, {'biggie': ['Ensure this value is greater than or equal to -9223372036854775808.']})
        bif = BigIntForm({'biggie': '9223372036854775807'})
        self.assertEqual(bif.is_valid(), True)
        bif = BigIntForm({'biggie': '9223372036854775808'})
        self.assertEqual(bif.is_valid(), False)
        self.assertEqual(bif.errors, {'biggie': ['Ensure this value is less than or equal to 9223372036854775807.']})

    @skipUnless(test_images, "PIL not installed")
    def test_image_field(self):
        # ImageField and FileField are nearly identical, but they differ slighty when
        # it comes to validation. This specifically tests that #6302 is fixed for
        # both file fields and image fields.

        with open(os.path.join(os.path.dirname(upath(__file__)), "test.png"), 'rb') as fp:
            image_data = fp.read()
        with open(os.path.join(os.path.dirname(upath(__file__)), "test2.png"), 'rb') as fp:
            image_data2 = fp.read()

        f = ImageFileForm(
                data={'description': 'An image'},
                files={'image': SimpleUploadedFile('test.png', image_data)})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(type(f.cleaned_data['image']), SimpleUploadedFile)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test.png')
        self.assertEqual(instance.width, 16)
        self.assertEqual(instance.height, 16)

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        f = ImageFileForm(
                data={'description': 'An image'},
                files={'image': SimpleUploadedFile('test.png', image_data)})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(type(f.cleaned_data['image']), SimpleUploadedFile)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test.png')
        self.assertEqual(instance.width, 16)
        self.assertEqual(instance.height, 16)

        # Edit an instance that already has the (required) image defined in the model. This will not
        # save the image again, but leave it exactly as it is.

        f = ImageFileForm(data={'description': 'Look, it changed'}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data['image'].name, 'tests/test.png')
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test.png')
        self.assertEqual(instance.height, 16)
        self.assertEqual(instance.width, 16)

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        # Override the file by uploading a new one.

        f = ImageFileForm(
                data={'description': 'Changed it'},
                files={'image': SimpleUploadedFile('test2.png', image_data2)}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test2.png')
        self.assertEqual(instance.height, 32)
        self.assertEqual(instance.width, 48)

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        instance.delete()

        f = ImageFileForm(
                data={'description': 'Changed it'},
                files={'image': SimpleUploadedFile('test2.png', image_data2)})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test2.png')
        self.assertEqual(instance.height, 32)
        self.assertEqual(instance.width, 48)

        # Delete the current file since this is not done by Django, but don't save
        # because the dimension fields are not null=True.
        instance.image.delete(save=False)
        instance.delete()

        # Test the non-required ImageField
        # Note: In Oracle, we expect a null ImageField to return '' instead of
        # None.
        if connection.features.interprets_empty_strings_as_nulls:
            expected_null_imagefield_repr = ''
        else:
            expected_null_imagefield_repr = None

        f = OptionalImageFileForm(data={'description': 'Test'})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, expected_null_imagefield_repr)
        self.assertEqual(instance.width, None)
        self.assertEqual(instance.height, None)

        f = OptionalImageFileForm(
                data={'description': 'And a final one'},
                files={'image': SimpleUploadedFile('test3.png', image_data)}, instance=instance)
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test3.png')
        self.assertEqual(instance.width, 16)
        self.assertEqual(instance.height, 16)

        # Editing the instance without re-uploading the image should not affect the image or its width/height properties
        f = OptionalImageFileForm(
                data={'description': 'New Description'},
                instance=instance)
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.description, 'New Description')
        self.assertEqual(instance.image.name, 'tests/test3.png')
        self.assertEqual(instance.width, 16)
        self.assertEqual(instance.height, 16)

        # Delete the current file since this is not done by Django.
        instance.image.delete()
        instance.delete()

        f = OptionalImageFileForm(
                data={'description': 'And a final one'},
                files={'image': SimpleUploadedFile('test4.png', image_data2)}
            )
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, 'tests/test4.png')
        self.assertEqual(instance.width, 48)
        self.assertEqual(instance.height, 32)
        instance.delete()
        # Test callable upload_to behavior that's dependent on the value of another field in the model
        f = ImageFileForm(
                data={'description': 'And a final one', 'path': 'foo'},
                files={'image': SimpleUploadedFile('test4.png', image_data)})
        self.assertEqual(f.is_valid(), True)
        instance = f.save()
        self.assertEqual(instance.image.name, 'foo/test4.png')
        instance.delete()

    def test_media_on_modelform(self):
        # Similar to a regular Form class you can define custom media to be used on
        # the ModelForm.
        f = ModelFormWithMedia()
        self.assertHTMLEqual(six.text_type(f.media), '''<link href="/some/form/css" type="text/css" media="all" rel="stylesheet" />
<script type="text/javascript" src="/some/form/javascript"></script>''')

        f = CommaSeparatedIntegerForm({'field': '1,2,3'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data, {'field': '1,2,3'})
        f = CommaSeparatedIntegerForm({'field': '1a,2'})
        self.assertEqual(f.errors, {'field': ['Enter only digits separated by commas.']})
        f = CommaSeparatedIntegerForm({'field': ',,,,'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data, {'field': ',,,,'})
        f = CommaSeparatedIntegerForm({'field': '1.2'})
        self.assertEqual(f.errors, {'field': ['Enter only digits separated by commas.']})
        f = CommaSeparatedIntegerForm({'field': '1,a,2'})
        self.assertEqual(f.errors, {'field': ['Enter only digits separated by commas.']})
        f = CommaSeparatedIntegerForm({'field': '1,,2'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data, {'field': '1,,2'})
        f = CommaSeparatedIntegerForm({'field': '1'})
        self.assertEqual(f.is_valid(), True)
        self.assertEqual(f.cleaned_data, {'field': '1'})

        # This Price instance generated by this form is not valid because the quantity
        # field is required, but the form is valid because the field is excluded from
        # the form. This is for backwards compatibility.

        form = PriceFormWithoutQuantity({'price': '6.00'})
        self.assertEqual(form.is_valid(), True)
        price = form.save(commit=False)
        with self.assertRaises(ValidationError):
            price.full_clean()

        # The form should not validate fields that it doesn't contain even if they are
        # specified using 'fields', not 'exclude'.
            class Meta:
                model = Price
                fields = ('price',)
        form = PriceFormWithoutQuantity({'price': '6.00'})
        self.assertEqual(form.is_valid(), True)

        # The form should still have an instance of a model that is not complete and
        # not saved into a DB yet.

        self.assertEqual(form.instance.price, Decimal('6.00'))
        self.assertEqual(form.instance.quantity is None, True)
        self.assertEqual(form.instance.pk is None, True)

        # Choices on CharField and IntegerField
        f = ArticleForm()
        with self.assertRaises(ValidationError):
            f.fields['status'].clean('42')

        f = ArticleStatusForm()
        with self.assertRaises(ValidationError):
            f.fields['status'].clean('z')

    def test_foreignkeys_which_use_to_field(self):
        apple = Inventory.objects.create(barcode=86, name='Apple')
        pear = Inventory.objects.create(barcode=22, name='Pear')
        core = Inventory.objects.create(barcode=87, name='Core', parent=apple)

        field = forms.ModelChoiceField(Inventory.objects.all(), to_field_name='barcode')
        self.assertEqual(tuple(field.choices), (
            ('', '---------'),
            (86, 'Apple'),
            (87, 'Core'),
            (22, 'Pear')))

        form = InventoryForm(instance=core)
        self.assertHTMLEqual(six.text_type(form['parent']), '''<select name="parent" id="id_parent">
<option value="">---------</option>
<option value="86" selected="selected">Apple</option>
<option value="87">Core</option>
<option value="22">Pear</option>
</select>''')
        data = model_to_dict(core)
        data['parent'] = '22'
        form = InventoryForm(data=data, instance=core)
        core = form.save()
        self.assertEqual(core.parent.name, 'Pear')

        class CategoryForm(forms.ModelForm):
            description = forms.CharField()
            class Meta:
                model = Category
                fields = ['description', 'url']

        self.assertEqual(list(CategoryForm.base_fields),
                         ['description', 'url'])

        self.assertHTMLEqual(six.text_type(CategoryForm()), '''<tr><th><label for="id_description">Description:</label></th><td><input type="text" name="description" id="id_description" /></td></tr>
<tr><th><label for="id_url">The URL:</label></th><td><input id="id_url" type="text" name="url" maxlength="40" /></td></tr>''')
        # to_field_name should also work on ModelMultipleChoiceField ##################

        field = forms.ModelMultipleChoiceField(Inventory.objects.all(), to_field_name='barcode')
        self.assertEqual(tuple(field.choices), ((86, 'Apple'), (87, 'Core'), (22, 'Pear')))
        self.assertQuerysetEqual(field.clean([86]), ['Apple'])

        form = SelectInventoryForm({'items': [87, 22]})
        self.assertEqual(form.is_valid(), True)
        self.assertEqual(len(form.cleaned_data), 1)
        self.assertQuerysetEqual(form.cleaned_data['items'], ['Core', 'Pear'])

    def test_model_field_that_returns_none_to_exclude_itself_with_explicit_fields(self):
        self.assertEqual(list(CustomFieldForExclusionForm.base_fields),
                         ['name'])
        self.assertHTMLEqual(six.text_type(CustomFieldForExclusionForm()),
                         '''<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" maxlength="10" /></td></tr>''')

    def test_iterable_model_m2m(self) :
        colour = Colour.objects.create(name='Blue')
        form = ColourfulItemForm()
        self.maxDiff = 1024
        self.assertHTMLEqual(
            form.as_p(),
            """<p><label for="id_name">Name:</label> <input id="id_name" type="text" name="name" maxlength="50" /></p>
        <p><label for="id_colours">Colours:</label> <select multiple="multiple" name="colours" id="id_colours">
        <option value="%(blue_pk)s">Blue</option>
        </select> <span class="helptext"> Hold down "Control", or "Command" on a Mac, to select more than one.</span></p>"""
            % {'blue_pk': colour.pk})
