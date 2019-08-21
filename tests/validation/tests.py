from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from django.test import TestCase
from django.utils.functional import lazy

from . import ValidationAssertions
from .models import (
    Article, Author, GenericIPAddressTestModel, GenericIPAddrUnpackUniqueTest,
    ModelToValidate,
)


class BaseModelValidationTests(ValidationAssertions, TestCase):

    def test_missing_required_field_raises_error(self):
        mtv = ModelToValidate(f_with_custom_validator=42)
        self.assertFailsValidation(mtv.full_clean, ['name', 'number'])

    def test_with_correct_value_model_validates(self):
        mtv = ModelToValidate(number=10, name='Some Name')
        self.assertIsNone(mtv.full_clean())

    def test_custom_validate_method(self):
        mtv = ModelToValidate(number=11)
        self.assertFailsValidation(mtv.full_clean, [NON_FIELD_ERRORS, 'name'])

    def test_wrong_FK_value_raises_error(self):
        mtv = ModelToValidate(number=10, name='Some Name', parent_id=3)
        self.assertFieldFailsValidationWithMessage(
            mtv.full_clean, 'parent',
            ['model to validate instance with id %r does not exist.' % mtv.parent_id]
        )
        mtv = ModelToValidate(number=10, name='Some Name', ufm_id='Some Name')
        self.assertFieldFailsValidationWithMessage(
            mtv.full_clean, 'ufm',
            ["unique fields model instance with unique_charfield %r does not exist." % mtv.name]
        )

    def test_correct_FK_value_validates(self):
        parent = ModelToValidate.objects.create(number=10, name='Some Name')
        mtv = ModelToValidate(number=10, name='Some Name', parent_id=parent.pk)
        self.assertIsNone(mtv.full_clean())

    def test_limited_FK_raises_error(self):
        # The limit_choices_to on the parent field says that a parent object's
        # number attribute must be 10, so this should fail validation.
        parent = ModelToValidate.objects.create(number=11, name='Other Name')
        mtv = ModelToValidate(number=10, name='Some Name', parent_id=parent.pk)
        self.assertFailsValidation(mtv.full_clean, ['parent'])

    def test_wrong_email_value_raises_error(self):
        mtv = ModelToValidate(number=10, name='Some Name', email='not-an-email')
        self.assertFailsValidation(mtv.full_clean, ['email'])

    def test_correct_email_value_passes(self):
        mtv = ModelToValidate(number=10, name='Some Name', email='valid@email.com')
        self.assertIsNone(mtv.full_clean())

    def test_wrong_url_value_raises_error(self):
        mtv = ModelToValidate(number=10, name='Some Name', url='not a url')
        self.assertFieldFailsValidationWithMessage(mtv.full_clean, 'url', ['Enter a valid URL.'])

    def test_text_greater_that_charfields_max_length_raises_errors(self):
        mtv = ModelToValidate(number=10, name='Some Name' * 100)
        self.assertFailsValidation(mtv.full_clean, ['name'])

    def test_malformed_slug_raises_error(self):
        mtv = ModelToValidate(number=10, name='Some Name', slug='##invalid##')
        self.assertFailsValidation(mtv.full_clean, ['slug'])

    def test_full_clean_does_not_mutate_exclude(self):
        mtv = ModelToValidate(f_with_custom_validator=42)
        exclude = ['number']
        self.assertFailsValidation(mtv.full_clean, ['name'], exclude=exclude)
        self.assertEqual(len(exclude), 1)
        self.assertEqual(exclude[0], 'number')


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        exclude = ['author']


class ModelFormsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name='Joseph Kocherhans')

    def test_partial_validation(self):
        # Make sure the "commit=False and set field values later" idiom still
        # works with model validation.
        data = {
            'title': 'The state of model validation',
            'pub_date': '2010-1-10 14:49:00'
        }
        form = ArticleForm(data)
        self.assertEqual(list(form.errors), [])
        article = form.save(commit=False)
        article.author = self.author
        article.save()

    def test_validation_with_empty_blank_field(self):
        # Since a value for pub_date wasn't provided and the field is
        # blank=True, model-validation should pass.
        # Also, Article.clean() should be run, so pub_date will be filled after
        # validation, so the form should save cleanly even though pub_date is
        # not allowed to be null.
        data = {
            'title': 'The state of model validation',
        }
        article = Article(author_id=self.author.id)
        form = ArticleForm(data, instance=article)
        self.assertEqual(list(form.errors), [])
        self.assertIsNotNone(form.instance.pub_date)
        article = form.save()

    def test_validation_with_invalid_blank_field(self):
        # Even though pub_date is set to blank=True, an invalid value was
        # provided, so it should fail validation.
        data = {
            'title': 'The state of model validation',
            'pub_date': 'never'
        }
        article = Article(author_id=self.author.id)
        form = ArticleForm(data, instance=article)
        self.assertEqual(list(form.errors), ['pub_date'])


class GenericIPAddressFieldTests(ValidationAssertions, TestCase):

    def test_correct_generic_ip_passes(self):
        giptm = GenericIPAddressTestModel(generic_ip="1.2.3.4")
        self.assertIsNone(giptm.full_clean())
        giptm = GenericIPAddressTestModel(generic_ip=" 1.2.3.4 ")
        self.assertIsNone(giptm.full_clean())
        giptm = GenericIPAddressTestModel(generic_ip="1.2.3.4\n")
        self.assertIsNone(giptm.full_clean())
        giptm = GenericIPAddressTestModel(generic_ip="2001::2")
        self.assertIsNone(giptm.full_clean())

    def test_invalid_generic_ip_raises_error(self):
        giptm = GenericIPAddressTestModel(generic_ip="294.4.2.1")
        self.assertFailsValidation(giptm.full_clean, ['generic_ip'])
        giptm = GenericIPAddressTestModel(generic_ip="1:2")
        self.assertFailsValidation(giptm.full_clean, ['generic_ip'])
        giptm = GenericIPAddressTestModel(generic_ip=1)
        self.assertFailsValidation(giptm.full_clean, ['generic_ip'])
        giptm = GenericIPAddressTestModel(generic_ip=lazy(lambda: 1, int))
        self.assertFailsValidation(giptm.full_clean, ['generic_ip'])

    def test_correct_v4_ip_passes(self):
        giptm = GenericIPAddressTestModel(v4_ip="1.2.3.4")
        self.assertIsNone(giptm.full_clean())

    def test_invalid_v4_ip_raises_error(self):
        giptm = GenericIPAddressTestModel(v4_ip="294.4.2.1")
        self.assertFailsValidation(giptm.full_clean, ['v4_ip'])
        giptm = GenericIPAddressTestModel(v4_ip="2001::2")
        self.assertFailsValidation(giptm.full_clean, ['v4_ip'])

    def test_correct_v6_ip_passes(self):
        giptm = GenericIPAddressTestModel(v6_ip="2001::2")
        self.assertIsNone(giptm.full_clean())

    def test_invalid_v6_ip_raises_error(self):
        giptm = GenericIPAddressTestModel(v6_ip="1.2.3.4")
        self.assertFailsValidation(giptm.full_clean, ['v6_ip'])
        giptm = GenericIPAddressTestModel(v6_ip="1:2")
        self.assertFailsValidation(giptm.full_clean, ['v6_ip'])

    def test_v6_uniqueness_detection(self):
        # These two addresses are the same with different syntax
        giptm = GenericIPAddressTestModel(generic_ip="2001::1:0:0:0:0:2")
        giptm.save()
        giptm = GenericIPAddressTestModel(generic_ip="2001:0:1:2")
        self.assertFailsValidation(giptm.full_clean, ['generic_ip'])

    def test_v4_unpack_uniqueness_detection(self):
        # These two are different, because we are not doing IPv4 unpacking
        giptm = GenericIPAddressTestModel(generic_ip="::ffff:10.10.10.10")
        giptm.save()
        giptm = GenericIPAddressTestModel(generic_ip="10.10.10.10")
        self.assertIsNone(giptm.full_clean())

        # These two are the same, because we are doing IPv4 unpacking
        giptm = GenericIPAddrUnpackUniqueTest(generic_v4unpack_ip="::ffff:18.52.18.52")
        giptm.save()
        giptm = GenericIPAddrUnpackUniqueTest(generic_v4unpack_ip="18.52.18.52")
        self.assertFailsValidation(giptm.full_clean, ['generic_v4unpack_ip'])

    def test_empty_generic_ip_passes(self):
        giptm = GenericIPAddressTestModel(generic_ip="")
        self.assertIsNone(giptm.full_clean())
        giptm = GenericIPAddressTestModel(generic_ip=None)
        self.assertIsNone(giptm.full_clean())
