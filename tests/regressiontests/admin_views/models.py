from django.db import models
from django.contrib import admin


class Article(models.Model):
    """
    A simple article to test admin views. Test backwards compabilty.
    """
    content = models.TextField()
    date = models.DateTimeField()
        

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('content', 'date')
    list_filter = ('date',)
        
admin.site.register(Article, ArticleAdmin)