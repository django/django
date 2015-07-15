from collections import defaultdict
from itertools import combinations

from django.conf import settings
from django.contrib.sessions.apps import SessionsConfig
from django.core import checks


@checks.register(SessionsConfig.checks_tag)
def check_names_conflict(app_configs=None, **kwargs):
    errors = []
    duplicate_pairs = []
    cookie_names = dict(
        SESSION_COOKIE_NAME=settings.SESSION_COOKIE_NAME,
        LANGUAGE_COOKIE_NAME=settings.LANGUAGE_COOKIE_NAME,
        CSRF_COOKIE_NAME=settings.CSRF_COOKIE_NAME,
    )

    # search for duplicates, start by generating flipped, multiple values dict
    flipped = defaultdict(set)
    for k, v in cookie_names.items():
        flipped[v].add(k)

    # create duplicates pairs with itertools.combinations
    for v in flipped.values():
        if len(v) > 1:
            duplicate_pairs.extend(combinations(v, 2))

    for pair in duplicate_pairs:
        pair = sorted(pair)
        errors.append(
            checks.Error(
                "The '%s' and '%s' settings must be different." % (pair[0], pair[1]),
                id='sessions.E001',
            )
        )

    return errors
