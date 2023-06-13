import os

FLATPAGES_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(os.path.dirname(__file__), "templates")],
        "OPTIONS": {
            "context_processors": ("django.contrib.auth.context_processors.auth",),
        },
    }
]
