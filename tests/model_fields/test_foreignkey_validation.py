"""
Tests for ForeignKey validation using base manager instead of default manager.
Refs: Issue where ForeignKey.validate() should use _base_manager instead of _default_manager
"""
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase


class ArticleManager(models.Manager):
    """Custom manager that filters out archived articles."""
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(archived=False)


class Article(models.Model):
    """Model with a custom default manager that filters archived items."""
    title = models.CharField(max_length=100)
    archived = models.BooleanField(default=False)

    # Don't include archived articles by default
    objects = ArticleManager()

    class Meta:
        app_label = 'model_fields'


class FavoriteArticle(models.Model):
    """Model with ForeignKey to Article."""
    article = models.ForeignKey(Article, on_delete=models.CASCADE)

    class Meta:
        app_label = 'model_fields'


class FavoriteArticleForm(forms.ModelForm):
    """Form that allows selecting archived articles."""
    class Meta:
        model = FavoriteArticle
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use the base manager to allow archived articles
        self.fields['article'].queryset = Article._base_manager.all()


class ForeignKeyValidationTests(TestCase):
    """
    Tests that ForeignKey.validate() uses _base_manager instead of _default_manager.

    This ensures that validation works correctly when forms need to use a different
    queryset than the model's default manager.
    """

    def setUp(self):
        """Set up test data."""
        # Create a regular article
        self.regular_article = Article.objects.create(title='Regular Article', archived=False)

        # Create an archived article
        self.archived_article = Article.objects.create(title='Archived Article', archived=True)

    def test_default_manager_excludes_archived(self):
        """Verify that the default manager filters out archived articles."""
        articles = Article.objects.all()
        self.assertEqual(articles.count(), 1)
        self.assertEqual(articles.first(), self.regular_article)

    def test_base_manager_includes_archived(self):
        """Verify that the base manager includes all articles."""
        articles = Article._base_manager.all()
        self.assertEqual(articles.count(), 2)

    def test_foreignkey_validation_with_regular_article(self):
        """Test that validation passes for non-archived article."""
        favorite = FavoriteArticle(article=self.regular_article)
        # Should not raise ValidationError
        favorite.full_clean()
        favorite.save()

        # Verify it was saved correctly
        self.assertEqual(FavoriteArticle.objects.count(), 1)
        self.assertEqual(FavoriteArticle.objects.first().article, self.regular_article)

    def test_foreignkey_validation_with_archived_article(self):
        """
        Test that validation passes for archived article.

        This is the key test - with the fix, ForeignKey.validate() should use
        _base_manager, so it should be able to find archived articles even though
        the default manager filters them out.
        """
        favorite = FavoriteArticle(article=self.archived_article)
        # Should not raise ValidationError (this would fail before the fix)
        favorite.full_clean()
        favorite.save()

        # Verify it was saved correctly
        self.assertEqual(FavoriteArticle.objects.count(), 1)
        self.assertEqual(FavoriteArticle.objects.first().article, self.archived_article)

    def test_form_validation_with_archived_article(self):
        """
        Test that ModelForm validation passes when using custom queryset.

        This tests the full scenario from the issue description where a form
        uses a custom queryset to allow archived articles.
        """
        form_data = {'article': str(self.archived_article.pk)}
        form = FavoriteArticleForm(data=form_data)

        # The form should be valid (would fail before the fix)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

        # Save the form and verify
        favorite = form.save()
        self.assertEqual(favorite.article, self.archived_article)

    def test_form_validation_with_regular_article(self):
        """Test that form validation still works for regular articles."""
        form_data = {'article': str(self.regular_article.pk)}
        form = FavoriteArticleForm(data=form_data)

        self.assertTrue(form.is_valid())
        favorite = form.save()
        self.assertEqual(favorite.article, self.regular_article)

    def test_direct_field_validation_archived(self):
        """
        Test ForeignKey field validation directly for archived article.

        This directly tests the validate() method that was changed.
        """
        field = FavoriteArticle._meta.get_field('article')
        favorite = FavoriteArticle(article=self.archived_article)

        # Should not raise ValidationError
        try:
            field.validate(self.archived_article.pk, favorite)
        except ValidationError:
            self.fail("ForeignKey validation raised ValidationError for archived article")

    def test_direct_field_validation_regular(self):
        """Test ForeignKey field validation directly for regular article."""
        field = FavoriteArticle._meta.get_field('article')
        favorite = FavoriteArticle(article=self.regular_article)

        # Should not raise ValidationError
        try:
            field.validate(self.regular_article.pk, favorite)
        except ValidationError:
            self.fail("ForeignKey validation raised ValidationError for regular article")

    def test_direct_field_validation_nonexistent(self):
        """Test that validation still fails for truly non-existent articles."""
        field = FavoriteArticle._meta.get_field('article')
        favorite = FavoriteArticle()

        # Use a PK that doesn't exist
        nonexistent_pk = 999999

        # Should raise ValidationError
        with self.assertRaises(ValidationError) as cm:
            field.validate(nonexistent_pk, favorite)

        # Check that the error contains the expected message about non-existent article
        error_message = str(cm.exception)
        self.assertIn('does not exist', error_message)
