from django.db import models
from django.contrib import admin
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

class Episode(models.Model):
    name = models.CharField(max_length=100)

class Media(models.Model):
    """
    Media that can associated to any object.
    """
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()
    url = models.URLField(verify_exists=False)

    def __unicode__(self):
        return self.url

class MediaInline(generic.GenericTabularInline):
    model = Media

class EpisodeAdmin(admin.ModelAdmin):
    inlines = [
        MediaInline,
    ]
admin.site.register(Episode, EpisodeAdmin)

#
# These models let us test the different GenericInline settings at
# different urls in the admin site.
#

#
# Generic inline with extra = 0
#

class EpisodeExtra(Episode):
    pass

class MediaExtraInline(generic.GenericTabularInline):
    model = Media
    extra = 0

admin.site.register(EpisodeExtra, inlines=[MediaExtraInline])

#
# Generic inline with extra and max_num
#

class EpisodeMaxNum(Episode):
    pass

class MediaMaxNumInline(generic.GenericTabularInline):
    model = Media
    extra = 5
    max_num = 2

admin.site.register(EpisodeMaxNum, inlines=[MediaMaxNumInline])

#
# Generic inline with exclude
#

class EpisodeExclude(Episode):
    pass

class MediaExcludeInline(generic.GenericTabularInline):
    model = Media
    exclude = ['url']

admin.site.register(EpisodeExclude, inlines=[MediaExcludeInline])

#
# Generic inline with unique_together
#

class PhoneNumber(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    phone_number = models.CharField(max_length=30)

    class Meta:
        unique_together = (('content_type', 'object_id', 'phone_number',),)

class Contact(models.Model):
    name = models.CharField(max_length=50)
    phone_numbers = generic.GenericRelation(PhoneNumber)

class PhoneNumberInline(generic.GenericTabularInline):
    model = PhoneNumber

admin.site.register(Contact, inlines=[PhoneNumberInline])

#
# Generic inline with can_delete=False
#

class EpisodePermanent(Episode):
    pass

class MediaPermanentInline(generic.GenericTabularInline):
    model = Media
    can_delete = False

admin.site.register(EpisodePermanent, inlines=[MediaPermanentInline])
