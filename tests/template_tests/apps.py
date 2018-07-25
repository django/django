from django.apps import AppConfig
from django.apps.assets import CSS, JS


class MyAdmin(AppConfig):
    name = 'django.contrib.admin'
    label = 'myadmin'
    assets = [
        CSS('css/admin.css'),
        JS('https://code.jquery.com/jquery-3.1.1.js'),
        JS('js/admin.js'),
    ]


class MyAuth(AppConfig):
    name = 'django.contrib.auth'
    label = 'myauth'
    assets = [
        CSS('css/auth.css'),
        JS('https://code.jquery.com/jquery-3.1.1.js'),
        JS('js/admin.js'),
    ]
