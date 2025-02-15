import os.path
from pathlib import Path

TEST_ROOT = os.path.dirname(__file__)

TEST_SETTINGS = {
    "MEDIA_URL": "media/",
    "STATIC_URL": "static/",
    "MEDIA_ROOT": os.path.join(TEST_ROOT, "project", "site_media", "media"),
    "STATIC_ROOT": os.path.join(TEST_ROOT, "project", "site_media", "static"),
    "STATICFILES_DIRS": [
        os.path.join(TEST_ROOT, "project", "documents"),
        ("prefix", os.path.join(TEST_ROOT, "project", "prefixed")),
        Path(TEST_ROOT) / "project" / "pathlib",
    ],
    "STATICFILES_FINDERS": [
        "thibaud.contrib.staticfiles.finders.FileSystemFinder",
        "thibaud.contrib.staticfiles.finders.AppDirectoriesFinder",
        "thibaud.contrib.staticfiles.finders.DefaultStorageFinder",
    ],
    "INSTALLED_APPS": [
        "thibaud.contrib.staticfiles",
        "staticfiles_tests",
        "staticfiles_tests.apps.test",
        "staticfiles_tests.apps.no_label",
    ],
    # In particular, AuthenticationMiddleware can't be used because
    # contrib.auth isn't in INSTALLED_APPS.
    "MIDDLEWARE": [],
}
