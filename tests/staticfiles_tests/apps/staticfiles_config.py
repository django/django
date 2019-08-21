from django.contrib.staticfiles.apps import StaticFilesConfig


class IgnorePatternsAppConfig(StaticFilesConfig):
    ignore_patterns = ['*.css', '*/vendor/*.js']
