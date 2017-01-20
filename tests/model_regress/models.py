from django.db import models

CHOICES = (
    (1, 'first'),
    (2, 'second'),
)


class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()
    status = models.IntegerField(blank=True, null=True, choices=CHOICES)
    misc_data = models.CharField(max_length=100, blank=True)
    article_text = models.TextField()

    class Meta:
        ordering = ('pub_date', 'headline')
        # A utf-8 verbose name (Ångström's Articles) to test they are valid.
        verbose_name = "\xc3\x85ngstr\xc3\xb6m's Articles"

    def __str__(self):
        return self.headline


class Movie(models.Model):
    # Test models with non-default primary keys / AutoFields #5218
    movie_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)


class Party(models.Model):
    when = models.DateField(null=True)


class Event(models.Model):
    when = models.DateTimeField()


class Department(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Worker(models.Model):
    department = models.ForeignKey(Department, models.CASCADE)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class BrokenStrMethod(models.Model):
    name = models.CharField(max_length=7)

    def __str__(self):
        # Intentionally broken (invalid start byte in byte string).
        return b'Name\xff: %s'.decode() % self.name


class NonAutoPK(models.Model):
    name = models.CharField(max_length=10, primary_key=True)


# Chained foreign keys with to_field produce incorrect query #18432
class Model1(models.Model):
    pkey = models.IntegerField(unique=True, db_index=True)


class Model2(models.Model):
    model1 = models.ForeignKey(Model1, models.CASCADE, unique=True, to_field='pkey')


class Model3(models.Model):
    model2 = models.ForeignKey(Model2, models.CASCADE, unique=True, to_field='model1')
