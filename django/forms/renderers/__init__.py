from django.conf import settings
from django.utils import lru_cache
from django.utils.module_loading import import_string


@lru_cache.lru_cache()
def get_default_renderer():
    renderer_class = import_string(settings.FORM_RENDERER)
    return renderer_class()
