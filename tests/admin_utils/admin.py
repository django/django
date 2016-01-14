from django.contrib import admin

from .models import Article, ArticleProxy, Site


class ArticleInline(admin.TabularInline):
    model = Article
    fields = ['title']


class SiteAdmin(admin.ModelAdmin):
    inlines = [ArticleInline]


site = admin.AdminSite(name='admin')
site.register(Article)
site.register(ArticleProxy)
site.register(Site, SiteAdmin)
