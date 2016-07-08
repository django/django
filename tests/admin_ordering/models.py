# -*- coding: utf-8 -*-
from django.contrib import admin
from django.db import models


class Band(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField()
    rank = models.IntegerField()

    class Meta:
        ordering = ('name',)


class Song(models.Model):
    band = models.ForeignKey(Band, models.CASCADE)
    name = models.CharField(max_length=100)
    duration = models.IntegerField()
    other_interpreters = models.ManyToManyField(Band, related_name='covers')

    class Meta:
        ordering = ('name',)


class SongInlineDefaultOrdering(admin.StackedInline):
    model = Song


class SongInlineNewOrdering(admin.StackedInline):
    model = Song
    ordering = ('duration', )


class DynOrderingBandAdmin(admin.ModelAdmin):

    def get_ordering(self, request):
        if request.user.is_superuser:
            return ['rank']
        else:
            return ['name']
