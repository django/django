from django.db import models

try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal    # Python 2.3 fallback

class Foo(models.Model):
    a = models.CharField(max_length=10)
    d = models.DecimalField(max_digits=5, decimal_places=3)

def get_foo():
    return Foo.objects.get(id=1)

class Bar(models.Model):
    b = models.CharField(max_length=10)
    a = models.ForeignKey(Foo, default=get_foo)

class Whiz(models.Model):
    CHOICES = (
        ('Group 1', (
                (1,'First'),
                (2,'Second'),
            )
        ),
        ('Group 2', (
                (3,'Third'),
                (4,'Fourth'),
            )
        ),
        (0,'Other'),
    )
    c = models.IntegerField(choices=CHOICES, null=True)
    
class BigD(models.Model):
    d = models.DecimalField(max_digits=38, decimal_places=30)

class BigS(models.Model):
    s = models.SlugField(max_length=255)