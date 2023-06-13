from django.db import models


class Article(models.Model):
    headline = models.CharField(max_length=100, default="Default headline")
    pub_date = models.DateTimeField()

    class Meta:
        app_label = "fixtures_model_package"
        ordering = ("-pub_date", "headline")

    def __str__(self):
        return self.headline
