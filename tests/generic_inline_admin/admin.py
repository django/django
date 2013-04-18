from __future__ import absolute_import

from django.contrib import admin
from django.contrib.contenttypes import generic

from .models import (Media, PhoneNumber, Episode, EpisodeExtra, Contact,
    Category, EpisodePermanent, EpisodeMaxNum)


site = admin.AdminSite(name="admin")

class MediaInline(generic.GenericTabularInline):
    model = Media


class EpisodeAdmin(admin.ModelAdmin):
    inlines = [
        MediaInline,
    ]


class MediaExtraInline(generic.GenericTabularInline):
    model = Media
    extra = 0


class MediaMaxNumInline(generic.GenericTabularInline):
    model = Media
    extra = 5
    max_num = 2


class PhoneNumberInline(generic.GenericTabularInline):
    model = PhoneNumber


class MediaPermanentInline(generic.GenericTabularInline):
    model = Media
    can_delete = False


site.register(Episode, EpisodeAdmin)
site.register(EpisodeExtra, inlines=[MediaExtraInline])
site.register(EpisodeMaxNum, inlines=[MediaMaxNumInline])
site.register(Contact, inlines=[PhoneNumberInline])
site.register(Category)
site.register(EpisodePermanent, inlines=[MediaPermanentInline])
