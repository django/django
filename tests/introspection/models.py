from django.db import models


class City(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Country(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=50)


class District(models.Model):
    city = models.ForeignKey(City, models.CASCADE, primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()
    facebook_user_id = models.BigIntegerField(null=True)
    raw_data = models.BinaryField(null=True)
    small_int = models.SmallIntegerField()
    interval = models.DurationField()

    class Meta:
        unique_together = ('first_name', 'last_name')

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField()
    body = models.TextField(default='')
    reporter = models.ForeignKey(Reporter, models.CASCADE)
    response_to = models.ForeignKey('self', models.SET_NULL, null=True)
    unmanaged_reporters = models.ManyToManyField(Reporter, through='ArticleReporter', related_name='+')

    class Meta:
        ordering = ('headline',)
        index_together = [
            ["headline", "pub_date"],
            ['headline', 'response_to', 'pub_date', 'reporter'],
        ]

    def __str__(self):
        return self.headline


class ArticleReporter(models.Model):
    article = models.ForeignKey(Article, models.CASCADE)
    reporter = models.ForeignKey(Reporter, models.CASCADE)

    class Meta:
        managed = False


class Comment(models.Model):
    ref = models.UUIDField(unique=True)
    article = models.ForeignKey(Article, models.CASCADE, db_index=True)
    email = models.EmailField()
    pub_date = models.DateTimeField()
    body = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['article', 'email', 'pub_date'], name='article_email_pub_date_uniq'),
        ]
        indexes = [
            models.Index(fields=['email', 'pub_date'], name='email_pub_date_idx'),
        ]


class CheckConstraintModel(models.Model):
    up_votes = models.PositiveIntegerField()
    voting_number = models.PositiveIntegerField(unique=True)

    class Meta:
        required_db_features = {
            'supports_table_check_constraints',
        }
        constraints = [
            models.CheckConstraint(name='up_votes_gte_0_check', check=models.Q(up_votes__gte=0)),
        ]
