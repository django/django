from django.conf import settings

def staticfiles(request):
    return {
        'STATICFILES_URL': settings.STATICFILES_URL,
    }
