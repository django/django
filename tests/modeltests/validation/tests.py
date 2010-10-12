from django import forms
from django.test import TestCase
from django.core.exceptions import NON_FIELD_ERRORS
from modeltests.validation import ValidationTestCase
from modeltests.validation.models import Author, Article, ModelToValidate

# Import other tests for this package.
from modeltests.validation.validators import TestModelsWithValidators
from modeltests.validation.test_unique import (GetUniqueCheckTests,
    PerformUniqueChecksTest)
from modeltests.validation.test_custom_messages import CustomMessagesTest


class BaseModelValidationTests(ValidationTestCase):

    def test_missing_required_field_raises_error(self):
        mtv = ModelToValidate(f_with_custom_validator=42)
        self.assertFailsValidation(mtv.full_clean, ['name', 'number'])

    def test_with_correct_value_model_validates(self):
        mtv = ModelToValidate(number=10, name='Some Name')
        self.assertEqual(None, mtv.full_clean())

    def test_custom_validate_method(self):
        mtv = ModelToValidate(number=11)
        self.assertFailsValidation(mtv.full_clean, [NON_FIELD_ERRORS, 'name'])

    def test_wrong_FK_value_raises_error(self):
        mtv=ModelToValidate(number=10, name='Some Name', parent_id=3)
        self.assertFailsValidation(mtv.full_clean, ['parent'])

    def test_correct_FK_value_validates(self):
        parent = ModelToValidate.objects.create(number=10, name='Some Name')
        mtv = ModelToValidate(number=10, name='Some Name', parent_id=parent.pk)
        self.assertEqual(None, mtv.full_clean())

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
        self.assertEqual(None, mtv.full_clean())

    def test_wrong_url_value_raises_error(self):
        mtv = ModelToValidate(number=10, name='Some Name', url='not a url')
        self.assertFieldFailsValidationWithMessage(mtv.full_clean, 'url', [u'Enter a valid value.'])

    def test_correct_url_but_nonexisting_gives_404(self):
        mtv = ModelToValidate(number=10, name='Some Name', url='http://google.com/we-love-microsoft.html')
        self.assertFieldFailsValidationWithMessage(mtv.full_clean, 'url', [u'This URL appears to be a broken link.'])

    def test_correct_url_value_passes(self):
        mtv = ModelToValidate(number=10, name='Some Name', url='http://www.djangoproject.com/')
        self.assertEqual(None, mtv.full_clean()) # This will fail if there's no Internet connection

    def test_text_greater_that_charfields_max_length_raises_erros(self):
        mtv = ModelToValidate(number=10, name='Some Name'*100)
        self.assertFailsValidation(mtv.full_clean, ['name',])

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        exclude = ['author']

class ModelFormsTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(name='Joseph Kocherhans')

    def test_partial_validation(self):
        # Make sure the "commit=False and set field values later" idiom still
        # works with model validation.
        data = {
            'title': 'The state of model validation',
            'pub_date': '2010-1-10 14:49:00'
        }
        form = ArticleForm(data)
        self.assertEqual(form.errors.keys(), [])
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
        self.assertEqual(form.errors.keys(), [])
        self.assertNotEqual(form.instance.pub_date, None)
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
        self.assertEqual(form.errors.keys(), ['pub_date'])
