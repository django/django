import os

FLATPAGES_TEMPLATES = [{
    'BACKEND': 'mango.template.backends.mango.MangoTemplates',
    'DIRS': [os.path.join(os.path.dirname(__file__), 'templates')],
    'OPTIONS': {
        'context_processors': (
            'mango.contrib.auth.context_processors.auth',
        ),
    },
}]
