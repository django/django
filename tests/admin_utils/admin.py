from django import forms
from django.contrib import admin

from .models import Article, ArticleProxy, Site


class ArticleAdminForm(forms.ModelForm):
    nolabel_form_field = forms.BooleanField(required=False)

    class Meta:
        model = Article
        fields = ["title"]

    @property
    def changed_data(self):
        data = super().changed_data
        if data:
            # Add arbitrary name to changed_data to test
            # change message construction.
            return data + ["not_a_form_field"]
        return data


class ArticleInline(admin.TabularInline):
    model = Article
    fields = ["title"]
    form = ArticleAdminForm


class SiteAdmin(admin.ModelAdmin):
    inlines = [ArticleInline]


site = admin.AdminSite(name="admin")
site.register(Article)
site.register(ArticleProxy)
site.register(Site, SiteAdmin)
