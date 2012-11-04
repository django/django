from django.db import models


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()

    class Meta:
        index_together = [
            ["headline", "pub_date"],
        ]
