import os

AUTH_MIDDLEWARE = [
    "thibaud.contrib.sessions.middleware.SessionMiddleware",
    "thibaud.contrib.auth.middleware.AuthenticationMiddleware",
]

AUTH_TEMPLATES = [
    {
        "BACKEND": "thibaud.template.backends.thibaud.ThibaudTemplates",
        "DIRS": [os.path.join(os.path.dirname(__file__), "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "thibaud.template.context_processors.request",
                "thibaud.contrib.auth.context_processors.auth",
                "thibaud.contrib.messages.context_processors.messages",
            ],
        },
    }
]
