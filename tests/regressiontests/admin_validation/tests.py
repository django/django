from django.contrib import admin
from django.contrib.admin.validation import validate
from django.test import TestCase

from models import Song


class ValidationTestCase(TestCase):
    def test_readonly_and_editable(self):
        class SongAdmin(admin.ModelAdmin):
            readonly_fields = ["original_release"]
            fieldsets = [
                (None, {
                    "fields": ["title", "original_release"],
                }),
            ]
        
        validate(SongAdmin, Song)
