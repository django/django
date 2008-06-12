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
    
    def changelist_view(self, request):
        "Test that extra_context works"
        return super(ArticleAdmin, self).changelist_view(request, extra_context={
            'extra_var': 'Hello!'
        })

class CustomArticle(Article):
    pass

class CustomArticleAdmin(admin.ModelAdmin):
    def changelist_view(self, request):
        "Test that extra_context works"
        return super(CustomArticleAdmin, self).changelist_view(request, extra_context={
            'extra_var': 'Hello!'
        })
        
admin.site.register(Article, ArticleAdmin)
admin.site.register(CustomArticle, CustomArticleAdmin)
