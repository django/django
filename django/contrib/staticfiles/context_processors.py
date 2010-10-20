from django.conf import settings

def staticfiles(request):
    return {
        'STATICFILES_URL': settings.STATICFILES_URL,
        'MEDIA_URL': settings.MEDIA_URL,
    }
