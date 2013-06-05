from django.db import models

# Create your models here.
PROXY_GROUPS = ('Terminal Server', 'Socks Proxy', 'Web Proxy')

class Group(models.Model):
    name = models.CharField(max_length=32)
    def __str__(self):
        return self.name

class Asset(models.Model):
    name = models.CharField(max_length=32)
    groups = models.ManyToManyField(Group)
    def __str__(self):
        return self.name

class Proxy(models.Model):
    asset = models.ForeignKey(Asset, limit_choices_to={'groups__name__in': PROXY_GROUPS}) # , 'distinct':True})
    port = models.PositiveIntegerField()
    def __str__(self):
        return "%s:%s" % (self.asset, self.port)
