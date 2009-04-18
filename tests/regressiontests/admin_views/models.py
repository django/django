# -*- coding: utf-8 -*-
import tempfile
import os
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.contrib import admin
from django.core.mail import EmailMessage

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

class Fabric(models.Model):
    NG_CHOICES = (
        ('Textured', (
                ('x', 'Horizontal'),
                ('y', 'Vertical'),
            )
        ),
        ('plain', 'Smooth'),
    )
    surface = models.CharField(max_length=20, choices=NG_CHOICES)

class FabricAdmin(admin.ModelAdmin):
    list_display = ('surface',)
    list_filter = ('surface',)

class Person(models.Model):
    GENDER_CHOICES = (
        (1, "Male"),
        (2, "Female"),
    )
    name = models.CharField(max_length=100)
    gender = models.IntegerField(choices=GENDER_CHOICES)
    alive = models.BooleanField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ["id"]

class PersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'gender', 'alive')
    list_editable = ('gender', 'alive')
    list_filter = ('gender',)
    search_fields = (u'name',)
    ordering = ["id"]

class Persona(models.Model):
    """
    A simple persona associated with accounts, to test inlining of related
    accounts which inherit from a common accounts class.
    """
    name = models.CharField(blank=False,  max_length=80)
    def __unicode__(self):
        return self.name

class Account(models.Model):
    """
    A simple, generic account encapsulating the information shared by all
    types of accounts.
    """
    username = models.CharField(blank=False,  max_length=80)
    persona = models.ForeignKey(Persona, related_name="accounts")
    servicename = u'generic service'

    def __unicode__(self):
        return "%s: %s" % (self.servicename, self.username)

class FooAccount(Account):
    """A service-specific account of type Foo."""
    servicename = u'foo'

class BarAccount(Account):
    """A service-specific account of type Bar."""
    servicename = u'bar'

class FooAccountAdmin(admin.StackedInline):
    model = FooAccount
    extra = 1

class BarAccountAdmin(admin.StackedInline):
    model = BarAccount
    extra = 1

class PersonaAdmin(admin.ModelAdmin):
    inlines = (
        FooAccountAdmin,
        BarAccountAdmin
    )

class Subscriber(models.Model):
    name = models.CharField(blank=False, max_length=80)
    email = models.EmailField(blank=False, max_length=175)

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.email)

class SubscriberAdmin(admin.ModelAdmin):
    actions = ['mail_admin']

    def mail_admin(self, request, selected):
        EmailMessage(
            'Greetings from a ModelAdmin action',
            'This is the test email from a admin action',
            'from@example.com',
            ['to@example.com']
        ).send()

class ExternalSubscriber(Subscriber):
    pass

class OldSubscriber(Subscriber):
    pass

def external_mail(modeladmin, request, selected):
    EmailMessage(
        'Greetings from a function action',
        'This is the test email from a function action',
        'from@example.com',
        ['to@example.com']
    ).send()

def redirect_to(modeladmin, request, selected):
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect('/some-where-else/')

class ExternalSubscriberAdmin(admin.ModelAdmin):
    actions = [external_mail, redirect_to]

class Media(models.Model):
    name = models.CharField(max_length=60)

class Podcast(Media):
    release_date = models.DateField()

class PodcastAdmin(admin.ModelAdmin):
    list_display = ('name', 'release_date')
    list_editable = ('release_date',)

    ordering = ('name',)

class Parent(models.Model):
    name = models.CharField(max_length=128)

class Child(models.Model):
    parent = models.ForeignKey(Parent, editable=False)
    name = models.CharField(max_length=30, blank=True)

class ChildInline(admin.StackedInline):
    model = Child

class ParentAdmin(admin.ModelAdmin):
    model = Parent
    inlines = [ChildInline]

class EmptyModel(models.Model):
    def __unicode__(self):
        return "Primary key = %s" % self.id

class EmptyModelAdmin(admin.ModelAdmin):
    def queryset(self, request):
        return super(EmptyModelAdmin, self).queryset(request).filter(pk__gt=1)

class OldSubscriberAdmin(admin.ModelAdmin):
    actions = None

temp_storage = FileSystemStorage(tempfile.mkdtemp())
UPLOAD_TO = os.path.join(temp_storage.location, 'test_upload')

class Gallery(models.Model):
    name = models.CharField(max_length=100)

class Picture(models.Model):
    name = models.CharField(max_length=100)
    image = models.FileField(storage=temp_storage, upload_to='test_upload')
    gallery = models.ForeignKey(Gallery, related_name="pictures")

class PictureInline(admin.TabularInline):
    model = Picture
    extra = 1

class GalleryAdmin(admin.ModelAdmin):
    inlines = [PictureInline]

class PictureAdmin(admin.ModelAdmin):
    pass

admin.site.register(Article, ArticleAdmin)
admin.site.register(CustomArticle, CustomArticleAdmin)
admin.site.register(Section, save_as=True, inlines=[ArticleInline])
admin.site.register(ModelWithStringPrimaryKey)
admin.site.register(Color)
admin.site.register(Thing, ThingAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Persona, PersonaAdmin)
admin.site.register(Subscriber, SubscriberAdmin)
admin.site.register(ExternalSubscriber, ExternalSubscriberAdmin)
admin.site.register(OldSubscriber, OldSubscriberAdmin)
admin.site.register(Podcast, PodcastAdmin)
admin.site.register(Parent, ParentAdmin)
admin.site.register(EmptyModel, EmptyModelAdmin)
admin.site.register(Fabric, FabricAdmin)
admin.site.register(Gallery, GalleryAdmin)
admin.site.register(Picture, PictureAdmin)

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
