try:
    from django.contrib.gis import admin
except ImportError:
    from django.contrib import admin

    admin.OSMGeoAdmin = admin.ModelAdmin
