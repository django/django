def importmaps(request):
    from django.contrib.importmap.base import get_importmaps

    return {"importmaps": get_importmaps()}
