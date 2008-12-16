# -*- coding: utf-8 -*-
from django.db import models
from django.contrib import admin

class Section(models.Model):
    """
    A simple section that links to articles, to test linking to related items
    in admin views.
    """
    name = models.CharField(max_length=100)

class Article(models.Model):
    """
    A simple article to test admin views. Test backwards compatibility.
    """
    title = models.CharField(max_length=100)
    content = models.TextField()
    date = models.DateTimeField()
    section = models.ForeignKey(Section)

    def __unicode__(self):
        return self.title
    
    def model_year(self):
        return self.date.year
    model_year.admin_order_field = 'date'

class Book(models.Model):
    """
    A simple book that has chapters.
    """
    name = models.CharField(max_length=100, verbose_name=u'¿Name?')

    def __unicode__(self):
        return self.name

class Promo(models.Model):
    name = models.CharField(max_length=100, verbose_name=u'¿Name?')
    book = models.ForeignKey(Book)

    def __unicode__(self):
        return self.name

class Chapter(models.Model):
    title = models.CharField(max_length=100, verbose_name=u'¿Title?')
    content = models.TextField()
    book = models.ForeignKey(Book)

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name = u'¿Chapter?'

class ChapterXtra1(models.Model):
    chap = models.OneToOneField(Chapter, verbose_name=u'¿Chap?')
    xtra = models.CharField(max_length=100, verbose_name=u'¿Xtra?') 

    def __unicode__(self):
        return u'¿Xtra1: %s' % self.xtra

class ChapterXtra2(models.Model):
    chap = models.OneToOneField(Chapter, verbose_name=u'¿Chap?')
    xtra = models.CharField(max_length=100, verbose_name=u'¿Xtra?') 

    def __unicode__(self):
        return u'¿Xtra2: %s' % self.xtra

def callable_year(dt_value):
    return dt_value.year
callable_year.admin_order_field = 'date'

class ArticleInline(admin.TabularInline):
    model = Article

class ChapterInline(admin.TabularInline):
    model = Chapter

class ArticleAdmin(admin.ModelAdmin):
    list_display = ('content', 'date', callable_year, 'model_year', 'modeladmin_year')
    list_filter = ('date',)

    def changelist_view(self, request):
        "Test that extra_context works"
        return super(ArticleAdmin, self).changelist_view(
            request, extra_context={
                'extra_var': 'Hello!'
            }
        )
        
    def modeladmin_year(self, obj):
        return obj.date.year
    modeladmin_year.admin_order_field = 'date'

class CustomArticle(models.Model):
    content = models.TextField()
    date = models.DateTimeField()

class CustomArticleAdmin(admin.ModelAdmin):
    """
    Tests various hooks for using custom templates and contexts.
    """
    change_list_template = 'custom_admin/change_list.html'
    change_form_template = 'custom_admin/change_form.html'
    object_history_template = 'custom_admin/object_history.html'
    delete_confirmation_template = 'custom_admin/delete_confirmation.html'

    def changelist_view(self, request):
        "Test that extra_context works"
        return super(CustomArticleAdmin, self).changelist_view(
            request, extra_context={
                'extra_var': 'Hello!'
            }
        )

class ModelWithStringPrimaryKey(models.Model):
    id = models.CharField(max_length=255, primary_key=True)

    def __unicode__(self):
        return self.id

class Color(models.Model):
    value = models.CharField(max_length=10)
    warm = models.BooleanField()   
    def __unicode__(self):
        return self.value

class Thing(models.Model):
    title = models.CharField(max_length=20)
    color = models.ForeignKey(Color, limit_choices_to={'warm': True})
    def __unicode__(self):
        return self.title

class ThingAdmin(admin.ModelAdmin):
    list_filter = ('color',)

admin.site.register(Article, ArticleAdmin)
admin.site.register(CustomArticle, CustomArticleAdmin)
admin.site.register(Section, inlines=[ArticleInline])
admin.site.register(ModelWithStringPrimaryKey)
admin.site.register(Color)
admin.site.register(Thing, ThingAdmin)

# We intentionally register Promo and ChapterXtra1 but not Chapter nor ChapterXtra2.
# That way we cover all four cases:
#     related ForeignKey object registered in admin
#     related ForeignKey object not registered in admin
#     related OneToOne object registered in admin
#     related OneToOne object not registered in admin
# when deleting Book so as exercise all four troublesome (w.r.t escaping
# and calling force_unicode to avoid problems on Python 2.3) paths through
# contrib.admin.util's get_deleted_objects function.
admin.site.register(Book, inlines=[ChapterInline])
admin.site.register(Promo)
admin.site.register(ChapterXtra1)
