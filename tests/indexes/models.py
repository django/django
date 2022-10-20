from django.db import models


class CurrentTranslation(models.ForeignObject):
    """
    Creates virtual relation to the translation with model cache enabled.
    """

    # Avoid validation
    requires_unique_target = False

    def __init__(self, to, on_delete, from_fields, to_fields, **kwargs):
        # Disable reverse relation
        kwargs["related_name"] = "+"
        # Set unique to enable model cache.
        kwargs["unique"] = True
        super().__init__(to, on_delete, from_fields, to_fields, **kwargs)


class ArticleTranslation(models.Model):

    article = models.ForeignKey("indexes.Article", models.CASCADE)
    article_no_constraint = models.ForeignKey(
        "indexes.Article", models.CASCADE, db_constraint=False, related_name="+"
    )
    language = models.CharField(max_length=10, unique=True)
    content = models.TextField()


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    published = models.BooleanField(default=False)

    # Add virtual relation to the ArticleTranslation model.
    translation = CurrentTranslation(
        ArticleTranslation, models.CASCADE, ["id"], ["article"]
    )

    class Meta:
        indexes = [models.Index(fields=["headline", "pub_date"])]


class IndexedArticle(models.Model):
    headline = models.CharField(max_length=100, db_index=True)
    body = models.TextField(db_index=True)
    slug = models.CharField(max_length=40, unique=True)

    class Meta:
        required_db_features = {"supports_index_on_text_field"}


class IndexedArticle2(models.Model):
    headline = models.CharField(max_length=100)
    body = models.TextField()
