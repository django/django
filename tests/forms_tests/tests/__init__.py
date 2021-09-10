import inspect

from django.test.utils import override_settings

TEST_SETTINGS = [
    {
        'FORM_RENDERER': 'django.forms.renderers.DjangoTemplates',
        'TEMPLATES': {'BACKEND': 'django.template.backends.django.DjangoTemplates'},
    },
    {
        'FORM_RENDERER': 'django.forms.renderers.Jinja2',
        'TEMPLATES': {'BACKEND': 'django.template.backends.jinja2.Jinja2'},
    },
]


def test_all_form_renderers():
    def wrapper(func):
        def inner(*args, **kwargs):
            for settings in TEST_SETTINGS:
                with override_settings(**settings):
                    func(*args, **kwargs)
        return inner

    def decorator(cls):
        for name, func in inspect.getmembers(cls, inspect.isfunction):
            if name.startswith('test_'):
                setattr(cls, name, wrapper(func))
        return cls
    return decorator
