"""
Tests for ForeignKey validation with custom managers.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import (
    ArticleWithCustomManager,
    FavoriteArticle,
    FavoriteArticleWithLimitChoices,
)


class ForeignKeyValidationWithCustomManagerTests(TestCase):
    """
    Test that ForeignKey validation uses the base manager rather than the
    default manager, allowing form validation to work correctly when a custom
    queryset is provided.
    """

    def test_foreignkey_validation_uses_base_manager(self):
        """
        ForeignKey.validate() should use _base_manager instead of
        _default_manager so that validation works even when the default
        manager filters out objects.
        """
        # Create an archived article
        archived_article = ArticleWithCustomManager.objects.create(
            title='Archived Article',
            archived=True
        )

        # Create a non-archived article
        active_article = ArticleWithCustomManager.objects.create(
            title='Active Article',
            archived=False
        )

        # Verify the default manager filters out archived articles
        self.assertEqual(ArticleWithCustomManager.objects.count(), 1)
        self.assertEqual(ArticleWithCustomManager._base_manager.count(), 2)

        # Test validation with an active article (should pass)
        favorite_active = FavoriteArticle(article_id=active_article.pk)
        favorite_active.full_clean()  # Should not raise ValidationError

        # Test validation with an archived article (should pass with base manager)
        favorite_archived = FavoriteArticle(article_id=archived_article.pk)
        # This should NOT raise a ValidationError because we're using _base_manager
        favorite_archived.full_clean()

    def test_foreignkey_form_validation_with_custom_queryset(self):
        """
        Test that a ModelForm can validate a ForeignKey field with a custom
        queryset that includes objects filtered out by the default manager.
        """
        # Create an archived article
        archived_article = ArticleWithCustomManager.objects.create(
            title='Archived Article',
            archived=True
        )

        # Create a form that allows selecting archived articles
        class FavoriteArticleForm(forms.ModelForm):
            class Meta:
                model = FavoriteArticle
                fields = '__all__'

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Use the base manager to allow archived articles
                self.fields['article'].queryset = ArticleWithCustomManager._base_manager.all()

        # Test form with archived article - should validate successfully
        form = FavoriteArticleForm(data={'article': archived_article.pk})
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_foreignkey_validation_respects_limit_choices_to(self):
        """
        Test that ForeignKey validation still respects limit_choices_to when
        using _base_manager.
        """
        # Create an archived but published article
        archived_published_article = ArticleWithCustomManager.objects.create(
            title='Archived Published Article',
            archived=True,
            status='published'
        )

        # Create an active draft article
        active_draft_article = ArticleWithCustomManager.objects.create(
            title='Active Draft Article',
            archived=False,
            status='draft'
        )

        # Validation should pass for archived published article
        # (base manager allows it, and it passes limit_choices_to)
        favorite_archived_published = FavoriteArticleWithLimitChoices(
            article_id=archived_published_article.pk
        )
        favorite_archived_published.full_clean()  # Should not raise

        # Validation should fail for draft article
        # (even though default manager includes it, it fails limit_choices_to)
        favorite_draft = FavoriteArticleWithLimitChoices(article_id=active_draft_article.pk)
        with self.assertRaises(ValidationError) as cm:
            favorite_draft.full_clean()
        self.assertIn('article', cm.exception.error_dict)

    def test_foreignkey_validation_with_nonexistent_object(self):
        """
        Test that ForeignKey validation still raises ValidationError for
        objects that don't exist at all (in base manager).
        """
        # Test with a non-existent ID
        favorite = FavoriteArticle(article_id=9999)
        with self.assertRaises(ValidationError) as cm:
            favorite.full_clean()
        self.assertIn('article', cm.exception.error_dict)
