from django.db import models


class Article(models.Model):
    title = models.CharField(max_length=100)
    pub_date = models.DateField()

    categories = models.ManyToManyField("Category", related_name="articles")

    def __unicode__(self):
        return self.title

class Comment(models.Model):
    article = models.ForeignKey(Article, related_name="comments")
    text = models.TextField()
    pub_date = models.DateField()
    approval_date = models.DateField(null=True)

    def __unicode__(self):
        return 'Comment to %s (%s)' % (self.article.title, self.pub_date)

class Category(models.Model):
    name = models.CharField(max_length=255)
