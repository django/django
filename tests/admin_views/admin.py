import datetime
from io import StringIO
from wsgiref.util import FileWrapper

from django import forms
from django.contrib import admin
from django.contrib.admin import BooleanFieldListFilter
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import models
from django.forms.models import BaseModelFormSet
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.decorators.common import no_append_slash

from .forms import MediaActionForm
from .models import (
    Actor,
    AdminOrderedAdminMethod,
    AdminOrderedCallable,
    AdminOrderedField,
    AdminOrderedModelMethod,
    Album,
    Answer,
    Answer2,
    Article,
    BarAccount,
    Book,
    Bookmark,
    Box,
    Category,
    Chapter,
    ChapterXtra1,
    Child,
    ChildOfReferer,
    Choice,
    City,
    Collector,
    Color,
    Color2,
    ComplexSortedPerson,
    Country,
    CoverLetter,
    CustomArticle,
    CyclicOne,
    CyclicTwo,
    DependentChild,
    DooHickey,
    EmptyModel,
    EmptyModelHidden,
    EmptyModelMixin,
    EmptyModelVisible,
    ExplicitlyProvidedPK,
    ExternalSubscriber,
    Fabric,
    FancyDoodad,
    FieldOverridePost,
    FilteredManager,
    FooAccount,
    FoodDelivery,
    FunkyTag,
    Gadget,
    Gallery,
    GenRelReference,
    Grommet,
    ImplicitlyGeneratedPK,
    Ingredient,
    InlineReference,
    InlineReferer,
    Inquisition,
    Language,
    Link,
    MainPrepopulated,
    ModelWithStringPrimaryKey,
    NotReferenced,
    OldSubscriber,
    OtherStory,
    Paper,
    Parent,
    ParentWithDependentChildren,
    ParentWithUUIDPK,
    Person,
    Persona,
    Picture,
    Pizza,
    Plot,
    PlotDetails,
    PlotProxy,
    PluggableSearchPerson,
    Podcast,
    Post,
    PrePopulatedPost,
    PrePopulatedPostLargeSlug,
    PrePopulatedSubPost,
    Promo,
    Question,
    ReadablePizza,
    ReadOnlyPizza,
    ReadOnlyRelatedField,
    Recipe,
    Recommendation,
    Recommender,
    ReferencedByGenRel,
    ReferencedByInline,
    ReferencedByParent,
    RelatedPrepopulated,
    RelatedWithUUIDPKModel,
    Report,
    Reservation,
    Restaurant,
    RowLevelChangePermissionModel,
    Section,
    ShortMessage,
    Simple,
    Sketch,
    Song,
    State,
    Story,
    StumpJoke,
    Subscriber,
    SuperVillain,
    Telegram,
    Thing,
    Topping,
    Traveler,
    UnchangeableObject,
    UndeletableObject,
    UnorderedObject,
    UserMessenger,
    UserProxy,
    Villain,
    Vodcast,
    Whatsit,
    Widget,
    Worker,
    WorkHour,
)


@admin.display(ordering="date")
def callable_year(dt_value):
    try:
        return dt_value.year
    except AttributeError:
        return None


class ArticleInline(admin.TabularInline):
    model = Article
    fk_name = "section"
    prepopulated_fields = {"title": ("content",)}
    fieldsets = (
        ("Some fields", {"classes": ("collapse",), "fields": ("title", "content")}),
        ("Some other fields", {"classes": ("wide",), "fields": ("date", "section")}),
    )


class ChapterInline(admin.TabularInline):
    model = Chapter


class ChapterXtra1Admin(admin.ModelAdmin):
    list_filter = (
        "chap",
        "chap__title",
        "chap__book",
        "chap__book__name",
        "chap__book__promo",
        "chap__book__promo__name",
        "guest_author__promo__book",
    )


class ArticleForm(forms.ModelForm):
    extra_form_field = forms.BooleanField(required=False)

    class Meta:
        fields = "__all__"
        model = Article


class ArticleAdminWithExtraUrl(admin.ModelAdmin):
    def get_urls(self):
        urlpatterns = super().get_urls()
        urlpatterns.append(
            path(
                "extra.json",
                self.admin_site.admin_view(self.extra_json),
                name="article_extra_json",
            )
        )
        return urlpatterns

    def extra_json(self, request):
        return JsonResponse({})


class ArticleAdmin(ArticleAdminWithExtraUrl):
    list_display = (
        "content",
        "date",
        callable_year,
        "model_year",
        "modeladmin_year",
        "model_year_reversed",
        "section",
        lambda obj: obj.title,
        "order_by_expression",
        "model_property_year",
        "model_month",
        "order_by_f_expression",
        "order_by_orderby_expression",
    )
    list_editable = ("section",)
    list_filter = ("date", "section")
    autocomplete_fields = ("section",)
    view_on_site = False
    form = ArticleForm
    fieldsets = (
        (
            "Some fields",
            {
                "classes": ("collapse",),
                "fields": ("title", "content", "extra_form_field"),
            },
        ),
        (
            "Some other fields",
            {"classes": ("wide",), "fields": ("date", "section", "sub_section")},
        ),
    )

    # These orderings aren't particularly useful but show that expressions can
    # be used for admin_order_field.
    @admin.display(ordering=models.F("date") + datetime.timedelta(days=3))
    def order_by_expression(self, obj):
        return obj.model_year

    @admin.display(ordering=models.F("date"))
    def order_by_f_expression(self, obj):
        return obj.model_year

    @admin.display(ordering=models.F("date").asc(nulls_last=True))
    def order_by_orderby_expression(self, obj):
        return obj.model_year

    def changelist_view(self, request):
        return super().changelist_view(request, extra_context={"extra_var": "Hello!"})

    @admin.display(ordering="date", description=None)
    def modeladmin_year(self, obj):
        return obj.date.year

    def delete_model(self, request, obj):
        EmailMessage(
            "Greetings from a deleted object",
            "I hereby inform you that some user deleted me",
            "from@example.com",
            ["to@example.com"],
        ).send()
        return super().delete_model(request, obj)

    def save_model(self, request, obj, form, change=True):
        EmailMessage(
            "Greetings from a created object",
            "I hereby inform you that some user created me",
            "from@example.com",
            ["to@example.com"],
        ).send()
        return super().save_model(request, obj, form, change)


class ArticleAdmin2(admin.ModelAdmin):
    def has_module_permission(self, request):
        return False


class RowLevelChangePermissionModelAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        """Only allow changing objects with even id number"""
        return request.user.is_staff and (obj is not None) and (obj.id % 2 == 0)

    def has_view_permission(self, request, obj=None):
        """Only allow viewing objects if id is a multiple of 3."""
        return request.user.is_staff and obj is not None and obj.id % 3 == 0


class CustomArticleAdmin(admin.ModelAdmin):
    """
    Tests various hooks for using custom templates and contexts.
    """

    change_list_template = "custom_admin/change_list.html"
    change_form_template = "custom_admin/change_form.html"
    add_form_template = "custom_admin/add_form.html"
    object_history_template = "custom_admin/object_history.html"
    delete_confirmation_template = "custom_admin/delete_confirmation.html"
    delete_selected_confirmation_template = (
        "custom_admin/delete_selected_confirmation.html"
    )
    popup_response_template = "custom_admin/popup_response.html"

    def changelist_view(self, request):
        return super().changelist_view(request, extra_context={"extra_var": "Hello!"})


class ThingAdmin(admin.ModelAdmin):
    list_filter = ("color", "color__warm", "color__value", "pub_date")


class InquisitionAdmin(admin.ModelAdmin):
    list_display = ("leader", "country", "expected", "sketch")

    @admin.display
    def sketch(self, obj):
        # A method with the same name as a reverse accessor.
        return "list-display-sketch"


class SketchAdmin(admin.ModelAdmin):
    raw_id_fields = ("inquisition", "defendant0", "defendant1")


class FabricAdmin(admin.ModelAdmin):
    list_display = ("surface",)
    list_filter = ("surface",)


class BasePersonModelFormSet(BaseModelFormSet):
    def clean(self):
        for person_dict in self.cleaned_data:
            person = person_dict.get("id")
            alive = person_dict.get("alive")
            if person and alive and person.name == "Grace Hopper":
                raise ValidationError("Grace is not a Zombie")


class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "gender", "alive")
    list_editable = ("gender", "alive")
    list_filter = ("gender",)
    search_fields = ("^name",)
    save_as = True

    def get_changelist_formset(self, request, **kwargs):
        return super().get_changelist_formset(
            request, formset=BasePersonModelFormSet, **kwargs
        )

    def get_queryset(self, request):
        # Order by a field that isn't in list display, to be able to test
        # whether ordering is preserved.
        return super().get_queryset(request).order_by("age")


class FooAccountAdmin(admin.StackedInline):
    model = FooAccount
    extra = 1


class BarAccountAdmin(admin.StackedInline):
    model = BarAccount
    extra = 1


class PersonaAdmin(admin.ModelAdmin):
    inlines = (FooAccountAdmin, BarAccountAdmin)


class SubscriberAdmin(admin.ModelAdmin):
    actions = ["mail_admin"]
    action_form = MediaActionForm

    def delete_queryset(self, request, queryset):
        SubscriberAdmin.overridden = True
        super().delete_queryset(request, queryset)

    @admin.action
    def mail_admin(self, request, selected):
        EmailMessage(
            "Greetings from a ModelAdmin action",
            "This is the test email from an admin action",
            "from@example.com",
            ["to@example.com"],
        ).send()


@admin.action(description="External mail (Another awesome action)")
def external_mail(modeladmin, request, selected):
    EmailMessage(
        "Greetings from a function action",
        "This is the test email from a function action",
        "from@example.com",
        ["to@example.com"],
    ).send()


@admin.action(description="Redirect to (Awesome action)")
def redirect_to(modeladmin, request, selected):
    from django.http import HttpResponseRedirect

    return HttpResponseRedirect("/some-where-else/")


@admin.action(description="Download subscription")
def download(modeladmin, request, selected):
    buf = StringIO("This is the content of the file")
    return StreamingHttpResponse(FileWrapper(buf))


@admin.action(description="No permission to run")
def no_perm(modeladmin, request, selected):
    return HttpResponse(content="No permission to perform this action", status=403)


class ExternalSubscriberAdmin(admin.ModelAdmin):
    actions = [redirect_to, external_mail, download, no_perm]


class PodcastAdmin(admin.ModelAdmin):
    list_display = ("name", "release_date")
    list_editable = ("release_date",)
    date_hierarchy = "release_date"
    ordering = ("name",)


class VodcastAdmin(admin.ModelAdmin):
    list_display = ("name", "released")
    list_editable = ("released",)

    ordering = ("name",)


class ChildInline(admin.StackedInline):
    model = Child


class ParentAdmin(admin.ModelAdmin):
    model = Parent
    inlines = [ChildInline]
    save_as = True
    list_display = (
        "id",
        "name",
    )
    list_display_links = ("id",)
    list_editable = ("name",)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        first_name, last_name = form.instance.name.split()
        for child in form.instance.child_set.all():
            if len(child.name.split()) < 2:
                child.name = child.name + " " + last_name
                child.save()


class EmptyModelAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk__gt=1)


class OldSubscriberAdmin(admin.ModelAdmin):
    actions = None


class PictureInline(admin.TabularInline):
    model = Picture
    extra = 1


class GalleryAdmin(admin.ModelAdmin):
    inlines = [PictureInline]


class PictureAdmin(admin.ModelAdmin):
    pass


class LanguageAdmin(admin.ModelAdmin):
    list_display = ["iso", "shortlist", "english_name", "name"]
    list_editable = ["shortlist"]


class RecommendationAdmin(admin.ModelAdmin):
    show_full_result_count = False
    search_fields = (
        "=titletranslation__text",
        "=the_recommender__titletranslation__text",
    )


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
    list_display = ("id", "collector", "order")
    list_editable = ("order",)


class CategoryInline(admin.StackedInline):
    model = Category


class CollectorAdmin(admin.ModelAdmin):
    inlines = [
        WidgetInline,
        DooHickeyInline,
        GrommetInline,
        WhatsitInline,
        FancyDoodadInline,
        CategoryInline,
    ]


class LinkInline(admin.TabularInline):
    model = Link
    extra = 1

    readonly_fields = ("posted", "multiline", "readonly_link_content")

    @admin.display
    def multiline(self, instance):
        return "InlineMultiline\ntest\nstring"


class SubPostInline(admin.TabularInline):
    model = PrePopulatedSubPost

    prepopulated_fields = {"subslug": ("subtitle",)}

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.published:
            return ("subslug",)
        return self.readonly_fields

    def get_prepopulated_fields(self, request, obj=None):
        if obj and obj.published:
            return {}
        return self.prepopulated_fields


class PrePopulatedPostAdmin(admin.ModelAdmin):
    list_display = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}

    inlines = [SubPostInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.published:
            return ("slug",)
        return self.readonly_fields

    def get_prepopulated_fields(self, request, obj=None):
        if obj and obj.published:
            return {}
        return self.prepopulated_fields


class PrePopulatedPostReadOnlyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}

    def has_change_permission(self, *args, **kwargs):
        return False


class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "public"]
    readonly_fields = (
        "posted",
        "awesomeness_level",
        "coolness",
        "value",
        "multiline",
        "multiline_html",
        lambda obj: "foo",
        "readonly_content",
    )

    inlines = [LinkInline]

    @admin.display
    def coolness(self, instance):
        if instance.pk:
            return "%d amount of cool." % instance.pk
        else:
            return "Unknown coolness."

    @admin.display(description="Value in $US")
    def value(self, instance):
        return 1000

    @admin.display
    def multiline(self, instance):
        return "Multiline\ntest\nstring"

    @admin.display
    def multiline_html(self, instance):
        return mark_safe("Multiline<br>\nhtml<br>\ncontent")


class FieldOverridePostForm(forms.ModelForm):
    model = FieldOverridePost

    class Meta:
        help_texts = {
            "posted": "Overridden help text for the date",
        }
        labels = {
            "public": "Overridden public label",
        }


class FieldOverridePostAdmin(PostAdmin):
    form = FieldOverridePostForm


class CustomChangeList(ChangeList):
    def get_queryset(self, request):
        return self.root_queryset.order_by("pk").filter(pk=9999)  # Doesn't exist


class GadgetAdmin(admin.ModelAdmin):
    def get_changelist(self, request, **kwargs):
        return CustomChangeList


class ToppingAdmin(admin.ModelAdmin):
    readonly_fields = ("pizzas",)


class PizzaAdmin(admin.ModelAdmin):
    readonly_fields = ("toppings",)


class ReadOnlyRelatedFieldAdmin(admin.ModelAdmin):
    readonly_fields = ("chapter", "language", "user")


class StudentAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class ReadOnlyPizzaAdmin(admin.ModelAdmin):
    readonly_fields = ("name", "toppings")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class WorkHourAdmin(admin.ModelAdmin):
    list_display = ("datum", "employee")
    list_filter = ("employee",)
    show_facets = admin.ShowFacets.ALWAYS


class FoodDeliveryAdmin(admin.ModelAdmin):
    list_display = ("reference", "driver", "restaurant")
    list_editable = ("driver", "restaurant")
    show_facets = admin.ShowFacets.NEVER


class CoverLetterAdmin(admin.ModelAdmin):
    """
    A ModelAdmin with a custom get_queryset() method that uses defer(), to test
    verbose_name display in messages shown after adding/editing CoverLetter
    instances. Note that the CoverLetter model defines a __str__ method.
    For testing fix for ticket #14529.
    """

    def get_queryset(self, request):
        return super().get_queryset(request).defer("date_written")


class PaperAdmin(admin.ModelAdmin):
    """
    A ModelAdmin with a custom get_queryset() method that uses only(), to test
    verbose_name display in messages shown after adding/editing Paper
    instances.
    For testing fix for ticket #14529.
    """

    def get_queryset(self, request):
        return super().get_queryset(request).only("title")


class ShortMessageAdmin(admin.ModelAdmin):
    """
    A ModelAdmin with a custom get_queryset() method that uses defer(), to test
    verbose_name display in messages shown after adding/editing ShortMessage
    instances.
    For testing fix for ticket #14529.
    """

    def get_queryset(self, request):
        return super().get_queryset(request).defer("timestamp")


class TelegramAdmin(admin.ModelAdmin):
    """
    A ModelAdmin with a custom get_queryset() method that uses only(), to test
    verbose_name display in messages shown after adding/editing Telegram
    instances. Note that the Telegram model defines a __str__ method.
    For testing fix for ticket #14529.
    """

    def get_queryset(self, request):
        return super().get_queryset(request).only("title")


class StoryForm(forms.ModelForm):
    class Meta:
        widgets = {"title": forms.HiddenInput}


class StoryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "content")
    list_display_links = ("title",)  # 'id' not in list_display_links
    list_editable = ("content",)
    form = StoryForm
    ordering = ["-id"]


class OtherStoryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "content")
    list_display_links = ("title", "id")  # 'id' in list_display_links
    list_editable = ("content",)
    ordering = ["-id"]


class ComplexSortedPersonAdmin(admin.ModelAdmin):
    list_display = ("name", "age", "is_employee", "colored_name")
    ordering = ("name",)

    @admin.display(ordering="name")
    def colored_name(self, obj):
        return format_html('<span style="color: #ff00ff;">{}</span>', obj.name)


class PluggableSearchPersonAdmin(admin.ModelAdmin):
    list_display = ("name", "age")
    search_fields = ("name",)

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )
        try:
            search_term_as_int = int(search_term)
        except ValueError:
            pass
        else:
            queryset |= self.model.objects.filter(age=search_term_as_int)
        return queryset, may_have_duplicates


class AlbumAdmin(admin.ModelAdmin):
    list_filter = ["title"]


class QuestionAdmin(admin.ModelAdmin):
    ordering = ["-posted"]
    search_fields = ["question"]
    autocomplete_fields = ["related_questions"]


class AnswerAdmin(admin.ModelAdmin):
    autocomplete_fields = ["question"]


class PrePopulatedPostLargeSlugAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}


class AdminOrderedFieldAdmin(admin.ModelAdmin):
    ordering = ("order",)
    list_display = ("stuff", "order")


class AdminOrderedModelMethodAdmin(admin.ModelAdmin):
    ordering = ("order",)
    list_display = ("stuff", "some_order")


class AdminOrderedAdminMethodAdmin(admin.ModelAdmin):
    @admin.display(ordering="order")
    def some_admin_order(self, obj):
        return obj.order

    ordering = ("order",)
    list_display = ("stuff", "some_admin_order")


@admin.display(ordering="order")
def admin_ordered_callable(obj):
    return obj.order


class AdminOrderedCallableAdmin(admin.ModelAdmin):
    ordering = ("order",)
    list_display = ("stuff", admin_ordered_callable)


class ReportAdmin(admin.ModelAdmin):
    def extra(self, request):
        return HttpResponse()

    def get_urls(self):
        # Corner case: Don't call parent implementation
        return [path("extra/", self.extra, name="cable_extra")]


class CustomTemplateBooleanFieldListFilter(BooleanFieldListFilter):
    template = "custom_filter_template.html"


class CustomTemplateFilterColorAdmin(admin.ModelAdmin):
    list_filter = (("warm", CustomTemplateBooleanFieldListFilter),)


# For Selenium Prepopulated tests -------------------------------------
class RelatedPrepopulatedInline1(admin.StackedInline):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("fk", "m2m"),
                    ("pubdate", "status"),
                    (
                        "name",
                        "slug1",
                        "slug2",
                    ),
                ),
            },
        ),
    )
    formfield_overrides = {models.CharField: {"strip": False}}
    model = RelatedPrepopulated
    extra = 1
    autocomplete_fields = ["fk", "m2m"]
    prepopulated_fields = {
        "slug1": ["name", "pubdate"],
        "slug2": ["status", "name"],
    }


class RelatedPrepopulatedInline2(admin.TabularInline):
    model = RelatedPrepopulated
    extra = 1
    autocomplete_fields = ["fk", "m2m"]
    prepopulated_fields = {
        "slug1": ["name", "pubdate"],
        "slug2": ["status", "name"],
    }


class RelatedPrepopulatedInline3(admin.TabularInline):
    model = RelatedPrepopulated
    extra = 0
    autocomplete_fields = ["fk", "m2m"]


class RelatedPrepopulatedStackedInlineNoFieldsets(admin.StackedInline):
    model = RelatedPrepopulated
    extra = 1
    prepopulated_fields = {
        "slug1": ["name", "pubdate"],
        "slug2": ["status"],
    }


class MainPrepopulatedAdmin(admin.ModelAdmin):
    inlines = [
        RelatedPrepopulatedInline1,
        RelatedPrepopulatedInline2,
        RelatedPrepopulatedInline3,
        RelatedPrepopulatedStackedInlineNoFieldsets,
    ]
    fieldsets = (
        (
            None,
            {"fields": (("pubdate", "status"), ("name", "slug1", "slug2", "slug3"))},
        ),
    )
    formfield_overrides = {models.CharField: {"strip": False}}
    prepopulated_fields = {
        "slug1": ["name", "pubdate"],
        "slug2": ["status", "name"],
        "slug3": ["name"],
    }


class UnorderedObjectAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    list_display_links = ["id"]
    list_editable = ["name"]
    list_per_page = 2


class UndeletableObjectAdmin(admin.ModelAdmin):
    def change_view(self, *args, **kwargs):
        kwargs["extra_context"] = {"show_delete": False}
        return super().change_view(*args, **kwargs)


class UnchangeableObjectAdmin(admin.ModelAdmin):
    def get_urls(self):
        # Disable change_view, but leave other urls untouched
        urlpatterns = super().get_urls()
        return [p for p in urlpatterns if p.name and not p.name.endswith("_change")]


@admin.display
def callable_on_unknown(obj):
    return obj.unknown


class AttributeErrorRaisingAdmin(admin.ModelAdmin):
    list_display = [callable_on_unknown]


class CustomManagerAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return FilteredManager.objects


class MessageTestingAdmin(admin.ModelAdmin):
    actions = [
        "message_debug",
        "message_info",
        "message_success",
        "message_warning",
        "message_error",
        "message_extra_tags",
    ]

    @admin.action
    def message_debug(self, request, selected):
        self.message_user(request, "Test debug", level="debug")

    @admin.action
    def message_info(self, request, selected):
        self.message_user(request, "Test info", level="info")

    @admin.action
    def message_success(self, request, selected):
        self.message_user(request, "Test success", level="success")

    @admin.action
    def message_warning(self, request, selected):
        self.message_user(request, "Test warning", level="warning")

    @admin.action
    def message_error(self, request, selected):
        self.message_user(request, "Test error", level="error")

    @admin.action
    def message_extra_tags(self, request, selected):
        self.message_user(request, "Test tags", extra_tags="extra_tag")


class ChoiceList(admin.ModelAdmin):
    list_display = ["choice"]
    readonly_fields = ["choice"]
    fields = ["choice"]


class DependentChildAdminForm(forms.ModelForm):
    """
    Issue #20522
    Form to test child dependency on parent object's validation
    """

    def clean(self):
        parent = self.cleaned_data.get("parent")
        if parent.family_name and parent.family_name != self.cleaned_data.get(
            "family_name"
        ):
            raise ValidationError(
                "Children must share a family name with their parents "
                + "in this contrived test case"
            )
        return super().clean()


class DependentChildInline(admin.TabularInline):
    model = DependentChild
    form = DependentChildAdminForm


class ParentWithDependentChildrenAdmin(admin.ModelAdmin):
    inlines = [DependentChildInline]


# Tests for ticket 11277 ----------------------------------


class FormWithoutHiddenField(forms.ModelForm):
    first = forms.CharField()
    second = forms.CharField()


class FormWithoutVisibleField(forms.ModelForm):
    first = forms.CharField(widget=forms.HiddenInput)
    second = forms.CharField(widget=forms.HiddenInput)


class FormWithVisibleAndHiddenField(forms.ModelForm):
    first = forms.CharField(widget=forms.HiddenInput)
    second = forms.CharField()


class EmptyModelVisibleAdmin(admin.ModelAdmin):
    form = FormWithoutHiddenField
    fieldsets = (
        (
            None,
            {
                "fields": (("first", "second"),),
            },
        ),
    )


class EmptyModelHiddenAdmin(admin.ModelAdmin):
    form = FormWithoutVisibleField
    fieldsets = EmptyModelVisibleAdmin.fieldsets


class EmptyModelMixinAdmin(admin.ModelAdmin):
    form = FormWithVisibleAndHiddenField
    fieldsets = EmptyModelVisibleAdmin.fieldsets


class CityInlineAdmin(admin.TabularInline):
    model = City
    view_on_site = False


class StateAdminForm(forms.ModelForm):
    nolabel_form_field = forms.BooleanField(required=False)

    class Meta:
        model = State
        fields = "__all__"
        labels = {"name": "State name (from form’s Meta.labels)"}

    @property
    def changed_data(self):
        data = super().changed_data
        if data:
            # Add arbitrary name to changed_data to test
            # change message construction.
            return data + ["not_a_form_field"]
        return data


class StateAdmin(admin.ModelAdmin):
    inlines = [CityInlineAdmin]
    form = StateAdminForm


class RestaurantInlineAdmin(admin.TabularInline):
    model = Restaurant
    view_on_site = True


class CityAdmin(admin.ModelAdmin):
    inlines = [RestaurantInlineAdmin]
    view_on_site = True

    def get_formset_kwargs(self, request, obj, inline, prefix):
        return {
            **super().get_formset_kwargs(request, obj, inline, prefix),
            "form_kwargs": {"initial": {"name": "overridden_name"}},
        }


class WorkerAdmin(admin.ModelAdmin):
    def view_on_site(self, obj):
        return "/worker/%s/%s/" % (obj.surname, obj.name)


class WorkerInlineAdmin(admin.TabularInline):
    model = Worker

    def view_on_site(self, obj):
        return "/worker_inline/%s/%s/" % (obj.surname, obj.name)


class RestaurantAdmin(admin.ModelAdmin):
    inlines = [WorkerInlineAdmin]
    view_on_site = False

    def get_changeform_initial_data(self, request):
        return {"name": "overridden_value"}


class FunkyTagAdmin(admin.ModelAdmin):
    list_display = ("name", "content_object")


class InlineReferenceInline(admin.TabularInline):
    model = InlineReference


class InlineRefererAdmin(admin.ModelAdmin):
    inlines = [InlineReferenceInline]


class PlotReadonlyAdmin(admin.ModelAdmin):
    readonly_fields = ("plotdetails",)


class GetFormsetsArgumentCheckingAdmin(admin.ModelAdmin):
    fields = ["name"]

    def add_view(self, request, *args, **kwargs):
        request.is_add_view = True
        return super().add_view(request, *args, **kwargs)

    def change_view(self, request, *args, **kwargs):
        request.is_add_view = False
        return super().change_view(request, *args, **kwargs)

    def get_formsets_with_inlines(self, request, obj=None):
        if request.is_add_view and obj is not None:
            raise Exception(
                "'obj' passed to get_formsets_with_inlines wasn't None during add_view"
            )
        if not request.is_add_view and obj is None:
            raise Exception(
                "'obj' passed to get_formsets_with_inlines was None during change_view"
            )
        return super().get_formsets_with_inlines(request, obj)


class CountryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


class TravelerAdmin(admin.ModelAdmin):
    autocomplete_fields = ["living_country"]


site = admin.AdminSite(name="admin")
site.site_url = "/my-site-url/"
site.register(Article, ArticleAdmin)
site.register(CustomArticle, CustomArticleAdmin)
site.register(
    Section,
    save_as=True,
    inlines=[ArticleInline],
    readonly_fields=["name_property"],
    search_fields=["name"],
)
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
site.register(FieldOverridePost, FieldOverridePostAdmin)
site.register(Gadget, GadgetAdmin)
site.register(Villain)
site.register(SuperVillain)
site.register(Plot)
site.register(PlotDetails)
site.register(PlotProxy, PlotReadonlyAdmin)
site.register(Bookmark)
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
site.register(UnchangeableObject, UnchangeableObjectAdmin)
site.register(State, StateAdmin)
site.register(City, CityAdmin)
site.register(Restaurant, RestaurantAdmin)
site.register(Worker, WorkerAdmin)
site.register(FunkyTag, FunkyTagAdmin)
site.register(ReferencedByParent)
site.register(ChildOfReferer)
site.register(ReferencedByInline)
site.register(InlineReferer, InlineRefererAdmin)
site.register(ReferencedByGenRel)
site.register(GenRelReference)
site.register(ParentWithUUIDPK)
site.register(RelatedPrepopulated, search_fields=["name"])
site.register(RelatedWithUUIDPKModel)
site.register(ReadOnlyRelatedField, ReadOnlyRelatedFieldAdmin)

# We intentionally register Promo and ChapterXtra1 but not Chapter nor ChapterXtra2.
# That way we cover all four cases:
#     related ForeignKey object registered in admin
#     related ForeignKey object not registered in admin
#     related OneToOne object registered in admin
#     related OneToOne object not registered in admin
# when deleting Book so as exercise all four paths through
# contrib.admin.utils's get_deleted_objects function.
site.register(Book, inlines=[ChapterInline])
site.register(Promo)
site.register(ChapterXtra1, ChapterXtra1Admin)
site.register(Pizza, PizzaAdmin)
site.register(ReadOnlyPizza, ReadOnlyPizzaAdmin)
site.register(ReadablePizza)
site.register(Topping, ToppingAdmin)
site.register(Album, AlbumAdmin)
site.register(Song)
site.register(Question, QuestionAdmin)
site.register(Answer, AnswerAdmin, date_hierarchy="question__posted")
site.register(Answer2, date_hierarchy="question__expires")
site.register(PrePopulatedPost, PrePopulatedPostAdmin)
site.register(ComplexSortedPerson, ComplexSortedPersonAdmin)
site.register(FilteredManager, CustomManagerAdmin)
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
site.register(ParentWithDependentChildren, ParentWithDependentChildrenAdmin)
site.register(EmptyModelHidden, EmptyModelHiddenAdmin)
site.register(EmptyModelVisible, EmptyModelVisibleAdmin)
site.register(EmptyModelMixin, EmptyModelMixinAdmin)
site.register(StumpJoke)
site.register(Recipe)
site.register(Ingredient)
site.register(NotReferenced)
site.register(ExplicitlyProvidedPK, GetFormsetsArgumentCheckingAdmin)
site.register(ImplicitlyGeneratedPK, GetFormsetsArgumentCheckingAdmin)
site.register(UserProxy)
site.register(Box)
site.register(Country, CountryAdmin)
site.register(Traveler, TravelerAdmin)

# Register core models we need in our tests
site.register(User, UserAdmin)
site.register(Group, GroupAdmin)

# Used to test URL namespaces
site2 = admin.AdminSite(name="namespaced_admin")
site2.register(User, UserAdmin)
site2.register(Group, GroupAdmin)
site2.register(ParentWithUUIDPK)
site2.register(
    RelatedWithUUIDPKModel,
    list_display=["pk", "parent"],
    list_editable=["parent"],
    raw_id_fields=["parent"],
)
site2.register(Person, save_as_continue=False)
site2.register(ReadOnlyRelatedField, ReadOnlyRelatedFieldAdmin)
site2.register(Language)

site7 = admin.AdminSite(name="admin7")
site7.register(Article, ArticleAdmin2)
site7.register(Section)
site7.register(PrePopulatedPost, PrePopulatedPostReadOnlyAdmin)
site7.register(
    Pizza,
    filter_horizontal=["toppings"],
    fieldsets=(
        (
            "Collapsible",
            {
                "classes": ["collapse"],
                "fields": ["toppings"],
            },
        ),
    ),
)
site7.register(
    Question,
    filter_horizontal=["related_questions"],
    fieldsets=(
        (
            "Not collapsible",
            {
                "fields": ["related_questions"],
            },
        ),
    ),
)


# Used to test ModelAdmin.sortable_by and get_sortable_by().
class ArticleAdmin6(admin.ModelAdmin):
    list_display = (
        "content",
        "date",
        callable_year,
        "model_year",
        "modeladmin_year",
        "model_year_reversed",
        "section",
    )
    sortable_by = ("date", callable_year)

    @admin.display(ordering="date")
    def modeladmin_year(self, obj):
        return obj.date.year


class ActorAdmin6(admin.ModelAdmin):
    list_display = ("name", "age")
    sortable_by = ("name",)

    def get_sortable_by(self, request):
        return ("age",)


class ChapterAdmin6(admin.ModelAdmin):
    list_display = ("title", "book")
    sortable_by = ()


class ColorAdmin6(admin.ModelAdmin):
    list_display = ("value",)

    def get_sortable_by(self, request):
        return ()


site6 = admin.AdminSite(name="admin6")
site6.register(Article, ArticleAdmin6)
site6.register(Actor, ActorAdmin6)
site6.register(Chapter, ChapterAdmin6)
site6.register(Color, ColorAdmin6)


class ArticleAdmin9(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        # Simulate that the user can't change a specific object.
        return obj is None


class ActorAdmin9(admin.ModelAdmin):
    def get_urls(self):
        # Opt-out of append slash for single model.
        urls = super().get_urls()
        for pattern in urls:
            pattern.callback = no_append_slash(pattern.callback)
        return urls


site9 = admin.AdminSite(name="admin9")
site9.register(Article, ArticleAdmin9)
site9.register(Actor, ActorAdmin9)

site10 = admin.AdminSite(name="admin10")
site10.final_catch_all_view = False
site10.register(Article, ArticleAdminWithExtraUrl)
