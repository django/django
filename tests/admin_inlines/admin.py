from __future__ import absolute_import

from django.contrib import admin
from django import forms

from .models import *

site = admin.AdminSite(name="admin")


class BookInline(admin.TabularInline):
    model = Author.books.through


class NonAutoPKBookTabularInline(admin.TabularInline):
    model = NonAutoPKBook


class NonAutoPKBookStackedInline(admin.StackedInline):
    model = NonAutoPKBook


class EditablePKBookTabularInline(admin.TabularInline):
    model = EditablePKBook


class EditablePKBookStackedInline(admin.StackedInline):
    model = EditablePKBook


class AuthorAdmin(admin.ModelAdmin):
    inlines = [BookInline,
        NonAutoPKBookTabularInline, NonAutoPKBookStackedInline,
        EditablePKBookTabularInline, EditablePKBookStackedInline]


class InnerInline(admin.StackedInline):
    model = Inner
    can_delete = False
    readonly_fields = ('readonly',) # For bug #13174 tests.


class HolderAdmin(admin.ModelAdmin):

    class Media:
        js = ('my_awesome_admin_scripts.js',)


class ReadOnlyInlineInline(admin.TabularInline):
    model = ReadOnlyInline
    readonly_fields = ['name']


class InnerInline2(admin.StackedInline):
    model = Inner2

    class Media:
        js = ('my_awesome_inline_scripts.js',)


class InnerInline3(admin.StackedInline):
    model = Inner3

    class Media:
        js = ('my_awesome_inline_scripts.js',)


class TitleForm(forms.ModelForm):

    def clean(self):
        cleaned_data = self.cleaned_data
        title1 = cleaned_data.get("title1")
        title2 = cleaned_data.get("title2")
        if title1 != title2:
            raise forms.ValidationError("The two titles must be the same")
        return cleaned_data


class TitleInline(admin.TabularInline):
    model = Title
    form = TitleForm
    extra = 1


class Inner4StackedInline(admin.StackedInline):
    model = Inner4Stacked


class Inner4TabularInline(admin.TabularInline):
    model = Inner4Tabular


class Holder4Admin(admin.ModelAdmin):
    inlines = [Inner4StackedInline, Inner4TabularInline]


class InlineWeakness(admin.TabularInline):
    model = ShoppingWeakness
    extra = 1


class QuestionInline(admin.TabularInline):
    model = Question
    readonly_fields=['call_me']

    def call_me(self, obj):
        return 'Callable in QuestionInline'


class PollAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]

    def call_me(self, obj):
        return 'Callable in PollAdmin'


class ChapterInline(admin.TabularInline):
    model = Chapter
    readonly_fields=['call_me']

    def call_me(self, obj):
        return 'Callable in ChapterInline'


class NovelAdmin(admin.ModelAdmin):
    inlines = [ChapterInline]


class ConsigliereInline(admin.TabularInline):
    model = Consigliere


class SottoCapoInline(admin.TabularInline):
    model = SottoCapo


class ProfileInline(admin.TabularInline):
    model = Profile
    extra = 1


# admin for #18433
class ChildModel1Inline(admin.TabularInline):
    model = ChildModel1


class ChildModel2Inline(admin.StackedInline):
    model = ChildModel2

# admin for #19425 and #18388
class BinaryTreeAdmin(admin.TabularInline):
    model = BinaryTree

    def get_extra(self, request, obj=None, **kwargs):
        extra = 2
        if obj:
            return extra - obj.binarytree_set.count()
        return extra

    def get_max_num(self, request, obj=None, **kwargs):
        max_num = 3
        if obj:
            return max_num - obj.binarytree_set.count()
        return max_num

# admin for #19524
class SightingInline(admin.TabularInline):
    model = Sighting

site.register(TitleCollection, inlines=[TitleInline])
# Test bug #12561 and #12778
# only ModelAdmin media
site.register(Holder, HolderAdmin, inlines=[InnerInline])
# ModelAdmin and Inline media
site.register(Holder2, HolderAdmin, inlines=[InnerInline2])
# only Inline media
site.register(Holder3, inlines=[InnerInline3])

site.register(Poll, PollAdmin)
site.register(Novel, NovelAdmin)
site.register(Fashionista, inlines=[InlineWeakness])
site.register(Holder4, Holder4Admin)
site.register(Author, AuthorAdmin)
site.register(CapoFamiglia, inlines=[ConsigliereInline, SottoCapoInline, ReadOnlyInlineInline])
site.register(ProfileCollection, inlines=[ProfileInline])
site.register(ParentModelWithCustomPk, inlines=[ChildModel1Inline, ChildModel2Inline])
site.register(BinaryTree, inlines=[BinaryTreeAdmin])
site.register(ExtraTerrestrial, inlines=[SightingInline])
