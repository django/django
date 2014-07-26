try:
    from functools import lru_cache
except ImportError:
    from django.utils.functools_lru_cache import lru_cache
