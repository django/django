from django.utils.functional import wraps


def boolean_check(warning_code):
    def decorator(check_func):
        @wraps(check_func)
        def inner():
            if not check_func():
                return set([warning_code])
            return set()
        return inner
    return decorator
