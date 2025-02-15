import os

FLATPAGES_TEMPLATES = [
    {
        "BACKEND": "thibaud.template.backends.thibaud.ThibaudTemplates",
        "DIRS": [os.path.join(os.path.dirname(__file__), "templates")],
        "OPTIONS": {
            "context_processors": ("thibaud.contrib.auth.context_processors.auth",),
        },
    }
]
