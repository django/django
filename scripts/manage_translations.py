#!/usr/bin/env python
#
# This Python file contains utility scripts to manage Django translations.
# It has to be run inside the django git root directory.
#
# The following commands are available:
#
# * update_catalogs: check for new strings in core and contrib catalogs, and
#                    output how much strings are new/changed.
#
# * lang_stats: output statistics for each catalog/language combination
#
# * fetch: fetch translations from transifex.com
#
# Each command support the --languages and --resources options to limit their
# operation to the specified language or resource. For example, to get stats
# for Spanish in contrib.admin, run:
#
#  $ python scripts/manage_translations.py lang_stats --language=es --resources=admin
#
# Also each command supports a --verbosity option to get progress feedback.

import json
import os
import subprocess
from argparse import ArgumentParser
from collections import defaultdict
from configparser import ConfigParser
from datetime import datetime
from itertools import product

import requests

import django
from django.conf import settings
from django.core.management import call_command

HAVE_JS = ["admin"]
LANG_OVERRIDES = {
    "zh_CN": "zh_Hans",
    "zh_TW": "zh_Hant",
}


def run(*args, verbosity=0, **kwargs):
    if verbosity > 1:
        print(f"\n** subprocess.run ** command: {args=} {kwargs=}")
    return subprocess.run(*args, **kwargs)


def get_api_token():
    # Read token from ENV, otherwise read from the ~/.transifexrc file.
    api_token = os.getenv("TRANSIFEX_API_TOKEN")
    if not api_token:
        parser = ConfigParser()
        parser.read(os.path.expanduser("~/.transifexrc"))
        api_token = parser.get("https://www.transifex.com", "token")

    assert api_token, "Please define the TRANSIFEX_API_TOKEN env var."
    return api_token


def get_api_response(endpoint, api_token=None, params=None, verbosity=0):
    if api_token is None:
        api_token = get_api_token()
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/json",
    }
    endpoint = endpoint.strip("/")
    url = f"https://rest.api.transifex.com/{endpoint}"
    if verbosity > 2:
        print(f"\n>>> GET {url=} {params=}")
    response = requests.get(url, headers=headers, params=params)
    if verbosity > 2:
        print(f">>>> GET {response=}\n")
    response.raise_for_status()
    return response.json()["data"]


def list_resources_with_updates(
    date_since, resources=None, languages=None, verbosity=0
):
    api_token = get_api_token()
    project = "o:django:p:django"
    date_since_iso = date_since.isoformat().strip("Z") + "Z"
    if verbosity:
        print(f"\n== Starting list_resources_with_updates at {date_since_iso=}")

    if not languages:
        languages = [  # List languages using Transifex projects API.
            d["attributes"]["code"]
            for d in get_api_response(
                f"projects/{project}/languages", api_token, verbosity=verbosity
            )
        ]
    if verbosity > 1:
        print(f"\n=== Languages to process: {languages=}")

    if not resources:
        resources = [  # List resources using Transifex resources API.
            d["attributes"]["slug"]
            for d in get_api_response(
                "resources",
                api_token,
                params={"filter[project]": project},
                verbosity=verbosity,
            )
        ]
    else:
        resources = [_tx_resource_slug_for_name(r) for r in resources]
    if verbosity > 1:
        print(f"\n=== Resources to process: {resources=}")

    resource_lang_changed = defaultdict(list)
    for lang, resource in product(languages, resources):
        if verbosity:
            print(f"\n=== Getting data for: {lang=} {resource=} {date_since_iso=}")
        data = get_api_response(
            "resource_translations",
            api_token,
            params={
                "filter[resource]": f"{project}:r:{resource}",
                "filter[language]": f"l:{lang}",
                "filter[date_translated][gt]": date_since_iso,
            },
            verbosity=verbosity,
        )
        local_resource = resource.replace("contrib-", "", 1)
        local_lang = lang  # XXX: LANG_OVERRIDES.get(lang, lang)
        if data:
            resource_lang_changed[local_resource].append(local_lang)
            if verbosity > 2:
                fname = f"{local_resource}-{local_lang}.json"
                with open(fname, "w") as f:
                    f.write(json.dumps(data, sort_keys=True, indent=2))
                print(f"==== Stored full data JSON in: {fname}")
        if verbosity > 1:
            print(f"==== Result for {local_resource=} {local_lang=}: {len(data)=}")

    return resource_lang_changed


def _get_locale_dirs(resources, include_core=True):
    """
    Return a tuple (contrib name, absolute path) for all locale directories,
    optionally including the django core catalog.
    If resources list is not None, filter directories matching resources content.
    """
    contrib_dir = os.path.join(os.getcwd(), "django", "contrib")
    dirs = []

    # Collect all locale directories
    for contrib_name in os.listdir(contrib_dir):
        path = os.path.join(contrib_dir, contrib_name, "locale")
        if os.path.isdir(path):
            dirs.append((contrib_name, path))
            if contrib_name in HAVE_JS:
                dirs.append(("%s-js" % contrib_name, path))
    if include_core:
        dirs.insert(0, ("core", os.path.join(os.getcwd(), "django", "conf", "locale")))

    # Filter by resources, if any
    if resources is not None:
        res_names = [d[0] for d in dirs]
        dirs = [ld for ld in dirs if ld[0] in resources]
        if len(resources) > len(dirs):
            print(
                "You have specified some unknown resources. "
                "Available resource names are: %s" % (", ".join(res_names),)
            )
            exit(1)
    return dirs


def _tx_resource_slug_for_name(name):
    """Return the Transifex resource slug for the given name."""
    if name != "core":
        name = f"contrib-{name}"
    return name


def _tx_resource_for_name(name):
    """Return the Transifex resource name."""
    return "django." + _tx_resource_slug_for_name(name)


def _check_diff(cat_name, base_path):
    """
    Output the approximate number of changed/added strings in the en catalog.
    """
    po_path = "%(path)s/en/LC_MESSAGES/django%(ext)s.po" % {
        "path": base_path,
        "ext": "js" if cat_name.endswith("-js") else "",
    }
    p = run(
        "git diff -U0 %s | egrep '^[-+]msgid' | wc -l" % po_path,
        capture_output=True,
        shell=True,
    )
    num_changes = int(p.stdout.strip())
    print("%d changed/added messages in '%s' catalog." % (num_changes, cat_name))


def update_catalogs(resources=None, languages=None, verbosity=0):
    """
    Update the en/LC_MESSAGES/django.po (main and contrib) files with
    new/updated translatable strings.
    """
    settings.configure()
    django.setup()
    if resources is not None:
        print("`update_catalogs` will always process all resources.")
    contrib_dirs = _get_locale_dirs(None, include_core=False)

    os.chdir(os.path.join(os.getcwd(), "django"))
    print("Updating en catalogs for Django and contrib apps...")
    call_command("makemessages", locale=["en"], verbosity=verbosity)
    print("Updating en JS catalogs for Django and contrib apps...")
    call_command("makemessages", locale=["en"], domain="djangojs", verbosity=verbosity)

    # Output changed stats
    _check_diff("core", os.path.join(os.getcwd(), "conf", "locale"))
    for name, dir_ in contrib_dirs:
        _check_diff(name, dir_)


def lang_stats(resources=None, languages=None, verbosity=0):
    """
    Output language statistics of committed translation files for each
    Django catalog.
    If resources is provided, it should be a list of translation resource to
    limit the output (e.g. ['core', 'gis']).
    """
    locale_dirs = _get_locale_dirs(resources)

    for name, dir_ in locale_dirs:
        print("\nShowing translations stats for '%s':" % name)
        langs = sorted(d for d in os.listdir(dir_) if not d.startswith("_"))
        for lang in langs:
            if languages and lang not in languages:
                continue
            # TODO: merge first with the latest en catalog
            po_path = "{path}/{lang}/LC_MESSAGES/django{ext}.po".format(
                path=dir_, lang=lang, ext="js" if name.endswith("-js") else ""
            )
            p = run(
                ["msgfmt", "-vc", "-o", "/dev/null", po_path],
                capture_output=True,
                env={"LANG": "C"},
                encoding="utf-8",
                verbosity=verbosity,
            )
            if p.returncode == 0:
                # msgfmt output stats on stderr
                print("%s: %s" % (lang, p.stderr.strip()))
            else:
                print(
                    "Errors happened when checking %s translation for %s:\n%s"
                    % (lang, name, p.stderr)
                )


def fetch(resources=None, languages=None, date_since=None, verbosity=0):
    """
    Fetch translations from Transifex, wrap long lines, generate mo files.
    """
    if date_since is None:
        resource_lang_mapping = {}
    else:
        # Filter resources and languages that were updates after `date_since`
        resource_lang_mapping = list_resources_with_updates(
            date_since=date_since,
            resources=resources,
            languages=languages,
            verbosity=verbosity,
        )
        resources = resource_lang_mapping.keys()

    locale_dirs = _get_locale_dirs(resources)
    errors = []

    for name, dir_ in locale_dirs:
        cmd = [
            "tx",
            "pull",
            "-r",
            _tx_resource_for_name(name),
            "-f",
            "--minimum-perc=5",
        ]
        per_resource_langs = resource_lang_mapping.get(name, languages)
        # Transifex pull
        if per_resource_langs is None:
            run([*cmd, "--all"], verbosity=verbosity)
            target_langs = sorted(
                d for d in os.listdir(dir_) if not d.startswith("_") and d != "en"
            )
        else:
            run([*cmd, "-l", ",".join(per_resource_langs)], verbosity=verbosity)
            target_langs = per_resource_langs

        target_langs = [LANG_OVERRIDES.get(d, d) for d in target_langs]

        # msgcat to wrap lines and msgfmt for compilation of .mo file
        for lang in target_langs:
            po_path = "%(path)s/%(lang)s/LC_MESSAGES/django%(ext)s.po" % {
                "path": dir_,
                "lang": lang,
                "ext": "js" if name.endswith("-js") else "",
            }
            if not os.path.exists(po_path):
                print(
                    "No %(lang)s translation for resource %(name)s"
                    % {"lang": lang, "name": name}
                )
                continue
            run(
                ["msgcat", "--no-location", "-o", po_path, po_path], verbosity=verbosity
            )
            msgfmt = run(
                ["msgfmt", "-c", "-o", "%s.mo" % po_path[:-3], po_path],
                verbosity=verbosity,
            )
            if msgfmt.returncode != 0:
                errors.append((name, lang))
    if errors:
        print("\nWARNING: Errors have occurred in following cases:")
        for resource, lang in errors:
            print("\tResource %s for language %s" % (resource, lang))
        exit(1)

    if verbosity:
        print("\nCOMPLETED.")


def add_common_arguments(parser):
    parser.add_argument(
        "-r",
        "--resources",
        action="append",
        help="limit operation to the specified resources",
    )
    parser.add_argument(
        "-l",
        "--languages",
        action="append",
        help="limit operation to the specified languages",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        default=1,
        type=int,
        choices=[0, 1, 2, 3],
        help=(
            "Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, "
            "3=very verbose output"
        ),
    )


if __name__ == "__main__":
    parser = ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="cmd", help="choose the operation to perform"
    )

    parser_update = subparsers.add_parser(
        "update_catalogs",
        help="update English django.po files with new/updated translatable strings",
    )
    add_common_arguments(parser_update)

    parser_stats = subparsers.add_parser(
        "lang_stats",
        help="print the approximate number of changed/added strings in the en catalog",
    )
    add_common_arguments(parser_stats)

    parser_fetch = subparsers.add_parser(
        "fetch",
        help="fetch translations from Transifex, wrap long lines, generate mo files",
    )
    add_common_arguments(parser_fetch)
    parser_fetch.add_argument(
        "-s",
        "--since",
        dest="date_since",
        metavar="YYYY-MM-DD",
        type=datetime.fromisoformat,
        help=(
            "fetch translations that were done after this date (ISO format YYYY-MM-DD)."
        ),
    )

    options = parser.parse_args()
    kwargs = options.__dict__
    cmd = kwargs.pop("cmd")
    eval(cmd)(**kwargs)
