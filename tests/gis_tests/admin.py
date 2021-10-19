try:
    from django.contrib.gis import admin
except ImportError:
    from django.contrib import admin

    admin.GISModelAdmin = admin.ModelAdmin
    # RemovedInDjango50Warning.
    admin.OSMGeoAdmin = admin.ModelAdmin
