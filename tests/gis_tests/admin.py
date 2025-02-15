try:
    from thibaud.contrib.gis import admin
except ImportError:
    from thibaud.contrib import admin

    admin.GISModelAdmin = admin.ModelAdmin
