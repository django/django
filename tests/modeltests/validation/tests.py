from __future__ import absolute_import

import warnings

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from django.test import TestCase

# Import the verify_exists_urls from the 'forms' test app
from regressiontests.forms.tests.fields import verify_exists_urls

from . import ValidationTestCase
from .models import (Author, Article, ModelToValidate,
    GenericIPAddressTestModel, GenericIPAddrUnpackUniqueTest)

# Import other tests for this package.
from .test_custom_messages import CustomMessagesTest
from .test_error_messages import ValidationMessagesTest
from .test_unique import GetUniqueCheckTests, PerformUniqueChecksTest
from .validators import TestModelsWithValidators


class BaseModelValidationTests(ValidationTestCase):

    def setUp(self):
        self.save_warnings_state()
        warnings.filterwarnings('ignore', category=DeprecationWarning,
                                module='django.core.validators')

    def tearDown(self):
        self.restore_warnings_state()

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

    #The tests below which use url_verify are deprecated
    def test_correct_url_but_nonexisting_gives_404(self):
        mtv = ModelToValidate(number=10, name='Some Name', url_verify='http://qa-dev.w3.org/link-testsuite/http.php?code=404')
        self.assertFieldFailsValidationWithMessage(mtv.full_clean, 'url_verify', [u'This URL appears to be a broken link.'])

    @verify_exists_urls(existing_urls=('http://www.google.com/',))
    def test_correct_url_value_passes(self):
        mtv = ModelToValidate(number=10, name='Some Name', url_verify='http://www.google.com/')
        self.assertEqual(None, mtv.full_clean()) # This will fail if there's no Internet connection

    @verify_exists_urls(existing_urls=('http://qa-dev.w3.org/link-testsuite/http.php?code=301',))
    def test_correct_url_with_redirect(self):
        mtv = ModelToValidate(number=10, name='Some Name', url_verify='http://qa-dev.w3.org/link-testsuite/http.php?code=301') #example.com is a redirect to iana.org now
        self.assertEqual(None, mtv.full_clean()) # This will fail if there's no Internet connection

    def test_correct_https_url_but_nonexisting(self):
        mtv = ModelToValidate(number=10, name='Some Name', url_verify='https://www.example.com/')
        self.assertFieldFailsValidationWithMessage(mtv.full_clean, 'url_verify', [u'This URL appears to be a broken link.'])

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


class GenericIPAddressFieldTests(ValidationTestCase):

    def test_correct_generic_ip_passes(self):
        giptm = GenericIPAddressTestModel(generic_ip="1.2.3.4")
        self.assertEqual(None, giptm.full_clean())
        giptm = GenericIPAddressTestModel(generic_ip="2001::2")
        self.assertEqual(None, giptm.full_clean())

    def test_invalid_generic_ip_raises_error(self):
        giptm = GenericIPAddressTestModel(generic_ip="294.4.2.1")
        self.assertFailsValidation(giptm.full_clean, ['generic_ip',])
        giptm = GenericIPAddressTestModel(generic_ip="1:2")
        self.assertFailsValidation(giptm.full_clean, ['generic_ip',])

    def test_correct_v4_ip_passes(self):
        giptm = GenericIPAddressTestModel(v4_ip="1.2.3.4")
        self.assertEqual(None, giptm.full_clean())

    def test_invalid_v4_ip_raises_error(self):
        giptm = GenericIPAddressTestModel(v4_ip="294.4.2.1")
        self.assertFailsValidation(giptm.full_clean, ['v4_ip',])
        giptm = GenericIPAddressTestModel(v4_ip="2001::2")
        self.assertFailsValidation(giptm.full_clean, ['v4_ip',])

    def test_correct_v6_ip_passes(self):
        giptm = GenericIPAddressTestModel(v6_ip="2001::2")
        self.assertEqual(None, giptm.full_clean())

    def test_invalid_v6_ip_raises_error(self):
        giptm = GenericIPAddressTestModel(v6_ip="1.2.3.4")
        self.assertFailsValidation(giptm.full_clean, ['v6_ip',])
        giptm = GenericIPAddressTestModel(v6_ip="1:2")
        self.assertFailsValidation(giptm.full_clean, ['v6_ip',])

    def test_v6_uniqueness_detection(self):
        # These two addresses are the same with different syntax
        giptm = GenericIPAddressTestModel(generic_ip="2001::1:0:0:0:0:2")
        giptm.save()
        giptm = GenericIPAddressTestModel(generic_ip="2001:0:1:2")
        self.assertFailsValidation(giptm.full_clean, ['generic_ip',])

    def test_v4_unpack_uniqueness_detection(self):
        # These two are different, because we are not doing IPv4 unpacking
        giptm = GenericIPAddressTestModel(generic_ip="::ffff:10.10.10.10")
        giptm.save()
        giptm = GenericIPAddressTestModel(generic_ip="10.10.10.10")
        self.assertEqual(None, giptm.full_clean())

        # These two are the same, because we are doing IPv4 unpacking
        giptm = GenericIPAddrUnpackUniqueTest(generic_v4unpack_ip="::ffff:18.52.18.52")
        giptm.save()
        giptm = GenericIPAddrUnpackUniqueTest(generic_v4unpack_ip="18.52.18.52")
        self.assertFailsValidation(giptm.full_clean, ['generic_v4unpack_ip',])
