from django.db import models

class Article(models.Model):
    """
    A simple Article model for testing
    """
    site = models.ForeignKey('sites.Site', related_name="admin_articles")
    title = models.CharField(max_length=100)
    title2 = models.CharField(max_length=100, verbose_name="another name")
    created = models.DateTimeField()

    def test_from_model(self):
        return "nothing"

    def test_from_model_with_override(self):
        return "nothing"
    test_from_model_with_override.short_description = "not What you Expect"

class Count(models.Model):
    num = models.PositiveSmallIntegerField()
    parent = models.ForeignKey('self', null=True)

    def __unicode__(self):
        return unicode(self.num)

class Event(models.Model):
    date = models.DateTimeField(auto_now_add=True)

class Location(models.Model):
    event = models.OneToOneField(Event, verbose_name='awesome event')

class Guest(models.Model):
    event = models.OneToOneField(Event)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "awesome guest"
