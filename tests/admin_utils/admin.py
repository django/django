from django.contrib import admin

from .models import Article, ArticleProxy

site = admin.AdminSite(name='admin')
site.register(Article)
site.register(ArticleProxy)
