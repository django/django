try:
    from mango.contrib.gis import admin
except ImportError:
    from mango.contrib import admin

    admin.OSMGeoAdmin = admin.ModelAdmin
