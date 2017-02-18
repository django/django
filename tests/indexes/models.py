from django.db import connection, models


class CurrentTranslation(models.ForeignObject):
    """
    Creates virtual relation to the translation with model cache enabled.
    """
    # Avoid validation
    requires_unique_target = False

    def __init__(self, to, from_fields, to_fields, **kwargs):
        # Disable reverse relation
        kwargs['related_name'] = '+'
        # Set unique to enable model cache.
        kwargs['unique'] = True
        super(CurrentTranslation, self).__init__(to, from_fields, to_fields, **kwargs)


class ArticleTranslation(models.Model):

    article = models.ForeignKey('indexes.Article')
    language = models.CharField(max_length=10, unique=True)
    content = models.TextField()


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()

    # Add virtual relation to the ArticleTranslation model.
    translation = CurrentTranslation(ArticleTranslation, ['id'], ['article'])

    class Meta:
        index_together = [
            ["headline", "pub_date"],
        ]


# Model for index_together being used only with single list
class IndexTogetherSingleList(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()

    class Meta:
        index_together = ["headline", "pub_date"]

# Indexing a TextField on Oracle or MySQL results in index creation error.
if connection.vendor == 'postgresql':
    class IndexedArticle(models.Model):
        headline = models.CharField(max_length=100, db_index=True)
        body = models.TextField(db_index=True)
        slug = models.CharField(max_length=40, unique=True)
