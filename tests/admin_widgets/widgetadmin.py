from django.contrib import admin
from django.contrib.admin.options import ForeignKeyAdminField

from . import models


class WidgetAdmin(admin.AdminSite):
    pass


class CarAdmin(admin.ModelAdmin):
    list_display = ['make', 'model', 'owner']
    list_editable = ['owner']


class CarForeignKeyAdminField(ForeignKeyAdminField):
    def formfield(self, **kwargs):
        queryset = models.Car.objects.filter(owner=self.request.user) if self.db_field.name == 'car' else None
        return super(CarForeignKeyAdminField, self).formfield(queryset=queryset, **kwargs)


class CarTireAdmin(admin.ModelAdmin):
    def _admin_fields(self):
        admin_fields = super(CarTireAdmin, self)._admin_fields()
        admin_fields.update({'foreignkey': CarForeignKeyAdminField})
        return admin_fields


class EventAdmin(admin.ModelAdmin):
    raw_id_fields = ['main_band', 'supporting_bands']


class AlbumAdmin(admin.ModelAdmin):
    fields = ('name', 'cover_art',)
    readonly_fields = ('cover_art',)


class SchoolAdmin(admin.ModelAdmin):
    filter_vertical = ('students',)
    filter_horizontal = ('alumni',)

site = WidgetAdmin(name='widget-admin')

site.register(models.User)
site.register(models.Car, CarAdmin)
site.register(models.CarTire, CarTireAdmin)

site.register(models.Member)
site.register(models.Band)
site.register(models.Event, EventAdmin)
site.register(models.Album, AlbumAdmin)

site.register(models.Inventory)

site.register(models.Bee)

site.register(models.Advisor)

site.register(models.School, SchoolAdmin)

site.register(models.Profile)
