from pathlib import Path

FLATPAGES_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [Path(__file__).parent / "templates"],
        "OPTIONS": {
            "context_processors": ("django.contrib.auth.context_processors.auth",),
        },
    }
]
