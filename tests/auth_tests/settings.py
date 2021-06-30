import os

AUTH_MIDDLEWARE = [
    'mango.contrib.sessions.middleware.SessionMiddleware',
    'mango.contrib.auth.middleware.AuthenticationMiddleware',
]

AUTH_TEMPLATES = [{
    'BACKEND': 'mango.template.backends.mango.MangoTemplates',
    'DIRS': [os.path.join(os.path.dirname(__file__), 'templates')],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'mango.template.context_processors.request',
            'mango.contrib.auth.context_processors.auth',
            'mango.contrib.messages.context_processors.messages',
        ],
    },
}]
