# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import tempfile
import os

from django import forms
from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.core.files.storage import FileSystemStorage
from django.core.mail import EmailMessage
from django.core.servers.basehttp import FileWrapper
from django.conf.urls import patterns, url
from django.db import models
from django.forms.models import BaseModelFormSet
from django.http import HttpResponse, StreamingHttpResponse
from django.contrib.admin import BooleanFieldListFilter
from django.utils.six import StringIO

from .models import (Article, Chapter, Account, Media, Child, Parent, Picture,
    Widget, DooHickey, Grommet, Whatsit, FancyDoodad, Category, Link,
    PrePopulatedPost, PrePopulatedSubPost, CustomArticle, Section,
    ModelWithStringPrimaryKey, Color, Thing, Actor, Inquisition, Sketch, Person,
    Persona, Subscriber, ExternalSubscriber, OldSubscriber, Vodcast, EmptyModel,
    Fabric, Gallery, Language, Recommendation, Recommender, Collector, Post,
    Gadget, Villain, SuperVillain, Plot, PlotDetails, CyclicOne, CyclicTwo,
    WorkHour, Reservation, FoodDelivery, RowLevelChangePermissionModel, Paper,
    CoverLetter, Story, OtherStory, Book, Promo, ChapterXtra1, Pizza, Topping,
    Album, Question, Answer, ComplexSortedPerson, PluggableSearchPerson, PrePopulatedPostLargeSlug,
    AdminOrderedField, AdminOrderedModelMethod, AdminOrderedAdminMethod,
    AdminOrderedCallable, Report, Color2, UnorderedObject, MainPrepopulated,
    RelatedPrepopulated, UndeletableObject, UserMessenger, Simple, Choice,
    ShortMessage, Telegram)


def callable_year(dt_value):
    try:
        return dt_value.year
    except AttributeError:
        return None
callable_year.admin_order_field = 'date'


class ArticleInline(admin.TabularInline):
    model = Article
    prepopulated_fields = {
        'title' : ('content',)
    }
    fieldsets=(
        ('Some fields', {
            'classes': ('collapse',),
            'fields': ('title', 'content')
        }),
        ('Some other fields', {
            'classes': ('wide',),
            'fields': ('date', 'section')
        })
    )

class ChapterInline(admin.TabularInline):
    model = Chapter


class ChapterXtra1Admin(admin.ModelAdmin):
    list_filter = ('chap',
                   'chap__title',
                   'chap__book',
                   'chap__book__name',
                   'chap__book__promo',
                   'chap__book__promo__name',)


class ArticleAdmin(admin.ModelAdmin):
    list_display = ('content', 'date', callable_year, 'model_year', 'modeladmin_year')
    list_filter = ('date', 'section')
    fieldsets=(
        ('Some fields', {
            'classes': ('collapse',),
            'fields': ('title', 'content')
        }),
        ('Some other fields', {
            'classes': ('wide',),
            'fields': ('date', 'section')
        })
    )

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
    modeladmin_year.short_description = None

    def delete_model(self, request, obj):
        EmailMessage(
            'Greetings from a deleted object',
            'I hereby inform you that some user deleted me',
            'from@example.com',
            ['to@example.com']
        ).send()
        return super(ArticleAdmin, self).delete_model(request, obj)

    def save_model(self, request, obj, form, change=True):
        EmailMessage(
            'Greetings from a created object',
            'I hereby inform you that some user created me',
            'from@example.com',
            ['to@example.com']
        ).send()
        return super(ArticleAdmin, self).save_model(request, obj, form, change)


class RowLevelChangePermissionModelAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        """ Only allow changing objects with even id number """
        return request.user.is_staff and (obj is not None) and (obj.id % 2 == 0)


class CustomArticleAdmin(admin.ModelAdmin):
    """
    Tests various hooks for using custom templates and contexts.
    """
    change_list_template = 'custom_admin/change_list.html'
    change_form_template = 'custom_admin/change_form.html'
    add_form_template = 'custom_admin/add_form.html'
    object_history_template = 'custom_admin/object_history.html'
    delete_confirmation_template = 'custom_admin/delete_confirmation.html'
    delete_selected_confirmation_template = 'custom_admin/delete_selected_confirmation.html'

    def changelist_view(self, request):
        "Test that extra_context works"
        return super(CustomArticleAdmin, self).changelist_view(
            request, extra_context={
                'extra_var': 'Hello!'
            }
        )


class ThingAdmin(admin.ModelAdmin):
    list_filter = ('color__warm', 'color__value', 'pub_date',)


class InquisitionAdmin(admin.ModelAdmin):
    list_display = ('leader', 'country', 'expected')


class SketchAdmin(admin.ModelAdmin):
    raw_id_fields = ('inquisition', 'defendant0', 'defendant1')


class FabricAdmin(admin.ModelAdmin):
    list_display = ('surface',)
    list_filter = ('surface',)


class BasePersonModelFormSet(BaseModelFormSet):
    def clean(self):
        for person_dict in self.cleaned_data:
            person = person_dict.get('id')
            alive = person_dict.get('alive')
            if person and alive and person.name == "Grace Hopper":
                raise forms.ValidationError("Grace is not a Zombie")


class PersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'gender', 'alive')
    list_editable = ('gender', 'alive')
    list_filter = ('gender',)
    search_fields = ('^name',)
    save_as = True

    def get_changelist_formset(self, request, **kwargs):
        return super(PersonAdmin, self).get_changelist_formset(request,
            formset=BasePersonModelFormSet, **kwargs)

    def get_queryset(self, request):
        # Order by a field that isn't in list display, to be able to test
        # whether ordering is preserved.
        return super(PersonAdmin, self).get_queryset(request).order_by('age')


class FooAccount(Account):
    """A service-specific account of type Foo."""
    servicename = 'foo'


class BarAccount(Account):
    """A service-specific account of type Bar."""
    servicename = 'bar'


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


class SubscriberAdmin(admin.ModelAdmin):
    actions = ['mail_admin']

    def mail_admin(self, request, selected):
        EmailMessage(
            'Greetings from a ModelAdmin action',
            'This is the test email from a admin action',
            'from@example.com',
            ['to@example.com']
        ).send()


def external_mail(modeladmin, request, selected):
    EmailMessage(
        'Greetings from a function action',
        'This is the test email from a function action',
        'from@example.com',
        ['to@example.com']
    ).send()
external_mail.short_description = 'External mail (Another awesome action)'


def redirect_to(modeladmin, request, selected):
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect('/some-where-else/')
redirect_to.short_description = 'Redirect to (Awesome action)'


def download(modeladmin, request, selected):
    buf = StringIO('This is the content of the file')
    return StreamingHttpResponse(FileWrapper(buf))
download.short_description = 'Download subscription'


def no_perm(modeladmin, request, selected):
    return HttpResponse(content='No permission to perform this action',
                        status=403)
no_perm.short_description = 'No permission to run'


class ExternalSubscriberAdmin(admin.ModelAdmin):
    actions = [redirect_to, external_mail, download, no_perm]


class Podcast(Media):
    release_date = models.DateField()

    class Meta:
        ordering = ('release_date',) # overridden in PodcastAdmin


class PodcastAdmin(admin.ModelAdmin):
    list_display = ('name', 'release_date')
    list_editable = ('release_date',)
    date_hierarchy = 'release_date'
    ordering = ('name',)


class VodcastAdmin(admin.ModelAdmin):
    list_display = ('name', 'released')
    list_editable = ('released',)

    ordering = ('name',)


class ChildInline(admin.StackedInline):
    model = Child


class ParentAdmin(admin.ModelAdmin):
    model = Parent
    inlines = [ChildInline]

    list_editable = ('name',)

    def save_related(self, request, form, formsets, change):
        super(ParentAdmin, self).save_related(request, form, formsets, change)
        first_name, last_name = form.instance.name.split()
        for child in form.instance.child_set.all():
            if len(child.name.split()) < 2:
                child.name = child.name + ' ' + last_name
                child.save()


class EmptyModelAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return super(EmptyModelAdmin, self).get_queryset(request).filter(pk__gt=1)


class OldSubscriberAdmin(admin.ModelAdmin):
    actions = None


temp_storage = FileSystemStorage(tempfile.mkdtemp(dir=os.environ['DJANGO_TEST_TEMP_DIR']))
UPLOAD_TO = os.path.join(temp_storage.location, 'test_upload')


class PictureInline(admin.TabularInline):
    model = Picture
    extra = 1


class GalleryAdmin(admin.ModelAdmin):
    inlines = [PictureInline]


class PictureAdmin(admin.ModelAdmin):
    pass


class LanguageAdmin(admin.ModelAdmin):
    list_display = ['iso', 'shortlist', 'english_name', 'name']
    list_editable = ['shortlist']


class RecommendationAdmin(admin.ModelAdmin):
    search_fields = ('=titletranslation__text', '=recommender__titletranslation__text',)


class WidgetInline(admin.StackedInline):
    model = Widget


class DooHickeyInline(admin.StackedInline):
    model = DooHickey


class GrommetInline(admin.StackedInline):
    model = Grommet


class WhatsitInline(admin.StackedInline):
    model = Whatsit


class FancyDoodadInline(admin.StackedInline):
    model = FancyDoodad


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'collector', 'order')
    list_editable = ('order',)


class CategoryInline(admin.StackedInline):
    model = Category


class CollectorAdmin(admin.ModelAdmin):
    inlines = [
        WidgetInline, DooHickeyInline, GrommetInline, WhatsitInline,
        FancyDoodadInline, CategoryInline
    ]


class LinkInline(admin.TabularInline):
    model = Link
    extra = 1

    readonly_fields = ("posted", "multiline")

    def multiline(self, instance):
        return "InlineMultiline\ntest\nstring"


class SubPostInline(admin.TabularInline):
    model = PrePopulatedSubPost

    prepopulated_fields = {
        'subslug' : ('subtitle',)
    }

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.published:
            return ('subslug',)
        return self.readonly_fields

    def get_prepopulated_fields(self, request, obj=None):
        if obj and obj.published:
            return {}
        return self.prepopulated_fields


class PrePopulatedPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug']
    prepopulated_fields = {
        'slug' : ('title',)
    }

    inlines = [SubPostInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.published:
            return ('slug',)
        return self.readonly_fields

    def get_prepopulated_fields(self, request, obj=None):
        if obj and obj.published:
            return {}
        return self.prepopulated_fields


class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'public']
    readonly_fields = (
        'posted', 'awesomeness_level', 'coolness', 'value', 'multiline',
        lambda obj: "foo"
    )

    inlines = [
        LinkInline
    ]

    def coolness(self, instance):
        if instance.pk:
            return "%d amount of cool." % instance.pk
        else:
            return "Unkown coolness."

    def value(self, instance):
        return 1000

    def multiline(self, instance):
        return "Multiline\ntest\nstring"

    value.short_description = 'Value in $US'


class CustomChangeList(ChangeList):
    def get_queryset(self, request):
        return self.root_queryset.filter(pk=9999) # Does not exist


class GadgetAdmin(admin.ModelAdmin):
    def get_changelist(self, request, **kwargs):
        return CustomChangeList


class ToppingAdmin(admin.ModelAdmin):
    readonly_fields = ('pizzas',)


class PizzaAdmin(admin.ModelAdmin):
    readonly_fields = ('toppings',)


class WorkHourAdmin(admin.ModelAdmin):
    list_display = ('datum', 'employee')
    list_filter = ('employee',)


class FoodDeliveryAdmin(admin.ModelAdmin):
    list_display=('reference', 'driver', 'restaurant')
    list_editable = ('driver', 'restaurant')


class CoverLetterAdmin(admin.ModelAdmin):
    """
    A ModelAdmin with a custom get_queryset() method that uses defer(), to test
    verbose_name display in messages shown after adding/editing CoverLetter
    instances.
    Note that the CoverLetter model defines a __unicode__ method.
    For testing fix for ticket #14529.
    """

    def get_queryset(self, request):
        return super(CoverLetterAdmin, self).get_queryset(request).defer('date_written')


class PaperAdmin(admin.ModelAdmin):
    """
    A ModelAdmin with a custom get_queryset() method that uses only(), to test
    verbose_name display in messages shown after adding/editing Paper
    instances.
    For testing fix for ticket #14529.
    """

    def get_queryset(self, request):
        return super(PaperAdmin, self).get_queryset(request).only('title')


class ShortMessageAdmin(admin.ModelAdmin):
    """
    A ModelAdmin with a custom get_queryset() method that uses defer(), to test
    verbose_name display in messages shown after adding/editing ShortMessage
    instances.
    For testing fix for ticket #14529.
    """

    def get_queryset(self, request):
        return super(ShortMessageAdmin, self).get_queryset(request).defer('timestamp')


class TelegramAdmin(admin.ModelAdmin):
    """
    A ModelAdmin with a custom get_queryset() method that uses only(), to test
    verbose_name display in messages shown after adding/editing Telegram
    instances.
    Note that the Telegram model defines a __unicode__ method.
    For testing fix for ticket #14529.
    """

    def get_queryset(self, request):
        return super(TelegramAdmin, self).get_queryset(request).only('title')


class StoryForm(forms.ModelForm):
    class Meta:
        widgets = {'title': forms.HiddenInput}


class StoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content')
    list_display_links = ('title',) # 'id' not in list_display_links
    list_editable = ('content', )
    form = StoryForm
    ordering = ["-pk"]


class OtherStoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'content')
    list_display_links = ('title', 'id') # 'id' in list_display_links
    list_editable = ('content', )
    ordering = ["-pk"]


class ComplexSortedPersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'is_employee', 'colored_name')
    ordering = ('name',)

    def colored_name(self, obj):
        return '<span style="color: #%s;">%s</span>' % ('ff00ff', obj.name)
    colored_name.allow_tags = True
    colored_name.admin_order_field = 'name'


class PluggableSearchPersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'age')
    search_fields = ('name',)

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(PluggableSearchPersonAdmin, self).get_search_results(request, queryset, search_term)
        try:
            search_term_as_int = int(search_term)
            queryset |= self.model.objects.filter(age=search_term_as_int)
        except:
            pass
        return queryset, use_distinct


class AlbumAdmin(admin.ModelAdmin):
    list_filter = ['title']


class WorkHourAdmin(admin.ModelAdmin):
    list_display = ('datum', 'employee')
    list_filter = ('employee',)


class PrePopulatedPostLargeSlugAdmin(admin.ModelAdmin):
    prepopulated_fields = {
        'slug' : ('title',)
    }


class AdminOrderedFieldAdmin(admin.ModelAdmin):
    ordering = ('order',)
    list_display = ('stuff', 'order')

class AdminOrderedModelMethodAdmin(admin.ModelAdmin):
    ordering = ('order',)
    list_display = ('stuff', 'some_order')

class AdminOrderedAdminMethodAdmin(admin.ModelAdmin):
    def some_admin_order(self, obj):
        return obj.order
    some_admin_order.admin_order_field = 'order'
    ordering = ('order',)
    list_display = ('stuff', 'some_admin_order')

def admin_ordered_callable(obj):
    return obj.order
admin_ordered_callable.admin_order_field = 'order'
class AdminOrderedCallableAdmin(admin.ModelAdmin):
    ordering = ('order',)
    list_display = ('stuff', admin_ordered_callable)

class ReportAdmin(admin.ModelAdmin):
    def extra(self, request):
        return HttpResponse()

    def get_urls(self):
        # Corner case: Don't call parent implementation
        return patterns('',
            url(r'^extra/$',
                self.extra,
                name='cable_extra'),
        )


class CustomTemplateBooleanFieldListFilter(BooleanFieldListFilter):
    template = 'custom_filter_template.html'

class CustomTemplateFilterColorAdmin(admin.ModelAdmin):
    list_filter = (('warm', CustomTemplateBooleanFieldListFilter),)


# For Selenium Prepopulated tests -------------------------------------
class RelatedPrepopulatedInline1(admin.StackedInline):
    fieldsets = (
        (None, {
            'fields': (('pubdate', 'status'), ('name', 'slug1', 'slug2',),)
        }),
    )
    model = RelatedPrepopulated
    extra = 1
    prepopulated_fields = {'slug1': ['name', 'pubdate'],
                           'slug2': ['status', 'name']}

class RelatedPrepopulatedInline2(admin.TabularInline):
    model = RelatedPrepopulated
    extra = 1
    prepopulated_fields = {'slug1': ['name', 'pubdate'],
                           'slug2': ['status', 'name']}

class MainPrepopulatedAdmin(admin.ModelAdmin):
    inlines = [RelatedPrepopulatedInline1, RelatedPrepopulatedInline2]
    fieldsets = (
        (None, {
            'fields': (('pubdate', 'status'), ('name', 'slug1', 'slug2',),)
        }),
    )
    prepopulated_fields = {'slug1': ['name', 'pubdate'],
                           'slug2': ['status', 'name']}


class UnorderedObjectAdmin(admin.ModelAdmin):
    list_display = ['name']
    list_editable = ['name']
    list_per_page = 2


class UndeletableObjectAdmin(admin.ModelAdmin):
    def change_view(self, *args, **kwargs):
        kwargs['extra_context'] = {'show_delete': False}
        return super(UndeletableObjectAdmin, self).change_view(*args, **kwargs)


def callable_on_unknown(obj):
    return obj.unknown


class AttributeErrorRaisingAdmin(admin.ModelAdmin):
    list_display = [callable_on_unknown, ]

class MessageTestingAdmin(admin.ModelAdmin):
    actions = ["message_debug", "message_info", "message_success",
               "message_warning", "message_error", "message_extra_tags"]

    def message_debug(self, request, selected):
        self.message_user(request, "Test debug", level="debug")

    def message_info(self, request, selected):
        self.message_user(request, "Test info", level="info")

    def message_success(self, request, selected):
        self.message_user(request, "Test success", level="success")

    def message_warning(self, request, selected):
        self.message_user(request, "Test warning", level="warning")

    def message_error(self, request, selected):
        self.message_user(request, "Test error", level="error")

    def message_extra_tags(self, request, selected):
        self.message_user(request, "Test tags", extra_tags="extra_tag")


class ChoiceList(admin.ModelAdmin):
    list_display = ['choice']
    readonly_fields = ['choice']
    fields = ['choice']


site = admin.AdminSite(name="admin")
site.register(Article, ArticleAdmin)
site.register(CustomArticle, CustomArticleAdmin)
site.register(Section, save_as=True, inlines=[ArticleInline])
site.register(ModelWithStringPrimaryKey)
site.register(Color)
site.register(Thing, ThingAdmin)
site.register(Actor)
site.register(Inquisition, InquisitionAdmin)
site.register(Sketch, SketchAdmin)
site.register(Person, PersonAdmin)
site.register(Persona, PersonaAdmin)
site.register(Subscriber, SubscriberAdmin)
site.register(ExternalSubscriber, ExternalSubscriberAdmin)
site.register(OldSubscriber, OldSubscriberAdmin)
site.register(Podcast, PodcastAdmin)
site.register(Vodcast, VodcastAdmin)
site.register(Parent, ParentAdmin)
site.register(EmptyModel, EmptyModelAdmin)
site.register(Fabric, FabricAdmin)
site.register(Gallery, GalleryAdmin)
site.register(Picture, PictureAdmin)
site.register(Language, LanguageAdmin)
site.register(Recommendation, RecommendationAdmin)
site.register(Recommender)
site.register(Collector, CollectorAdmin)
site.register(Category, CategoryAdmin)
site.register(Post, PostAdmin)
site.register(Gadget, GadgetAdmin)
site.register(Villain)
site.register(SuperVillain)
site.register(Plot)
site.register(PlotDetails)
site.register(CyclicOne)
site.register(CyclicTwo)
site.register(WorkHour, WorkHourAdmin)
site.register(Reservation)
site.register(FoodDelivery, FoodDeliveryAdmin)
site.register(RowLevelChangePermissionModel, RowLevelChangePermissionModelAdmin)
site.register(Paper, PaperAdmin)
site.register(CoverLetter, CoverLetterAdmin)
site.register(ShortMessage, ShortMessageAdmin)
site.register(Telegram, TelegramAdmin)
site.register(Story, StoryAdmin)
site.register(OtherStory, OtherStoryAdmin)
site.register(Report, ReportAdmin)
site.register(MainPrepopulated, MainPrepopulatedAdmin)
site.register(UnorderedObject, UnorderedObjectAdmin)
site.register(UndeletableObject, UndeletableObjectAdmin)

# We intentionally register Promo and ChapterXtra1 but not Chapter nor ChapterXtra2.
# That way we cover all four cases:
#     related ForeignKey object registered in admin
#     related ForeignKey object not registered in admin
#     related OneToOne object registered in admin
#     related OneToOne object not registered in admin
# when deleting Book so as exercise all four troublesome (w.r.t escaping
# and calling force_text to avoid problems on Python 2.3) paths through
# contrib.admin.util's get_deleted_objects function.
site.register(Book, inlines=[ChapterInline])
site.register(Promo)
site.register(ChapterXtra1, ChapterXtra1Admin)
site.register(Pizza, PizzaAdmin)
site.register(Topping, ToppingAdmin)
site.register(Album, AlbumAdmin)
site.register(Question)
site.register(Answer)
site.register(PrePopulatedPost, PrePopulatedPostAdmin)
site.register(ComplexSortedPerson, ComplexSortedPersonAdmin)
site.register(PluggableSearchPerson, PluggableSearchPersonAdmin)
site.register(PrePopulatedPostLargeSlug, PrePopulatedPostLargeSlugAdmin)
site.register(AdminOrderedField, AdminOrderedFieldAdmin)
site.register(AdminOrderedModelMethod, AdminOrderedModelMethodAdmin)
site.register(AdminOrderedAdminMethod, AdminOrderedAdminMethodAdmin)
site.register(AdminOrderedCallable, AdminOrderedCallableAdmin)
site.register(Color2, CustomTemplateFilterColorAdmin)
site.register(Simple, AttributeErrorRaisingAdmin)
site.register(UserMessenger, MessageTestingAdmin)
site.register(Choice, ChoiceList)

# Register core models we need in our tests
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
site.register(User, UserAdmin)
site.register(Group, GroupAdmin)

# Used to test URL namespaces
site2 = admin.AdminSite(name="namespaced_admin")
site2.register(User, UserAdmin)
site2.register(Group, GroupAdmin)
