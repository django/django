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

import os
from argparse import ArgumentParser
from collections import defaultdict
from configparser import ConfigParser
from datetime import datetime
from subprocess import run

import requests

import django
from django.conf import settings
from django.core.management import call_command

HAVE_JS = ["admin"]
LANG_OVERRIDES = {
    "zh_CN": "zh_Hans",
    "zh_TW": "zh_Hant",
}


def list_resources_with_updates(date_since, date_skip=None, verbose=False):
    resource_lang_changed = defaultdict(list)
    resource_lang_unchanged = defaultdict(list)

    # Read token from ENV, otherwise read from the ~/.transifexrc file.
    api_token = os.getenv("TRANSIFEX_API_TOKEN")
    if not api_token:
        parser = ConfigParser()
        parser.read(os.path.expanduser("~/.transifexrc"))
        api_token = parser.get("https://www.transifex.com", "token")

    assert api_token, "Please define the TRANSIFEX_API_TOKEN env var."
    headers = {"Authorization": f"Bearer {api_token}"}
    base_url = "https://rest.api.transifex.com"
    base_params = {"filter[project]": "o:django:p:django"}

    resources_url = base_url + "/resources"
    resource_stats_url = base_url + "/resource_language_stats"

    response = requests.get(resources_url, headers=headers, params=base_params)
    assert response.ok, response.content
    data = response.json()["data"]

    for item in data:
        if item["type"] != "resources":
            continue
        resource_id = item["id"]
        resource_name = item["attributes"]["name"]
        params = base_params.copy()
        params.update({"filter[resource]": resource_id})
        stats = requests.get(resource_stats_url, headers=headers, params=params)
        stats_data = stats.json()["data"]
        for lang_data in stats_data:
            lang_id = lang_data["id"].split(":")[-1]
            lang_attributes = lang_data["attributes"]
            last_update = lang_attributes["last_translation_update"]
            if verbose:
                print(
                    f"CHECKING {resource_name} for {lang_id=} updated on {last_update}"
                )
            if last_update is None:
                resource_lang_unchanged[resource_name].append(lang_id)
                continue

            last_update = datetime.strptime(last_update, "%Y-%m-%dT%H:%M:%SZ")
            if last_update > date_since and (
                date_skip is None or last_update.date() != date_skip.date()
            ):
                if verbose:
                    print(f"=> CHANGED {lang_attributes=} {date_skip=}")
                resource_lang_changed[resource_name].append(lang_id)
            else:
                resource_lang_unchanged[resource_name].append(lang_id)

    if verbose:
        unchanged = "\n".join(
            f"\n * resource {res} languages {' '.join(sorted(langs))}"
            for res, langs in resource_lang_unchanged.items()
        )
        print(f"== SUMMARY for unchanged resources ==\n{unchanged}")

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


def _tx_resource_for_name(name):
    """Return the Transifex resource name"""
    if name == "core":
        return "django.core"
    else:
        return "django.contrib-%s" % name


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


def update_catalogs(resources=None, languages=None):
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
    call_command("makemessages", locale=["en"])
    print("Updating en JS catalogs for Django and contrib apps...")
    call_command("makemessages", locale=["en"], domain="djangojs")

    # Output changed stats
    _check_diff("core", os.path.join(os.getcwd(), "conf", "locale"))
    for name, dir_ in contrib_dirs:
        _check_diff(name, dir_)


def lang_stats(resources=None, languages=None):
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
            )
            if p.returncode == 0:
                # msgfmt output stats on stderr
                print("%s: %s" % (lang, p.stderr.strip()))
            else:
                print(
                    "Errors happened when checking %s translation for %s:\n%s"
                    % (lang, name, p.stderr)
                )


def fetch(resources=None, languages=None):
    """
    Fetch translations from Transifex, wrap long lines, generate mo files.
    """
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
        # Transifex pull
        if languages is None:
            run(cmd + ["--all"])
            target_langs = sorted(
                d for d in os.listdir(dir_) if not d.startswith("_") and d != "en"
            )
        else:
            for lang in languages:
                run(cmd + ["-l", lang])
            target_langs = languages

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
            run(["msgcat", "--no-location", "-o", po_path, po_path])
            msgfmt = run(["msgfmt", "-c", "-o", "%s.mo" % po_path[:-3], po_path])
            if msgfmt.returncode != 0:
                errors.append((name, lang))
    if errors:
        print("\nWARNING: Errors have occurred in following cases:")
        for resource, lang in errors:
            print("\tResource %s for language %s" % (resource, lang))
        exit(1)


def fetch_since(date_since, date_skip=None, verbose=False, dry_run=False):
    """
    Fetch translations from Transifex that were modified since the given date.
    """
    changed = list_resources_with_updates(
        date_since=date_since, date_skip=date_skip, verbose=verbose
    )
    if verbose:
        print(f"== SUMMARY for changed resources {dry_run=} ==\n")
    for res, langs in changed.items():
        if verbose:
            print(f"\n * resource {res} languages {' '.join(sorted(langs))}")
        if not dry_run:
            fetch(resources=[res], languages=sorted(langs))
    if not changed and verbose:
        print(f"\n No resource changed since {date_since}")


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

    parser_fetch = subparsers.add_parser(
        "fetch_since",
        help=(
            "fetch translations from Transifex modified since a given date "
            "(for all languages and all resources)"
        ),
    )
    parser_fetch.add_argument("-v", "--verbose", action="store_true")
    parser_fetch.add_argument(
        "-s",
        "--since",
        required=True,
        dest="date_since",
        metavar="YYYY-MM-DD",
        type=datetime.fromisoformat,
        help="fetch new translations since this date (ISO format YYYY-MM-DD).",
    )
    parser_fetch.add_argument(
        "--skip",
        dest="date_skip",
        metavar="YYYY-MM-DD",
        type=datetime.fromisoformat,
        help="skip changes from this date (ISO format YYYY-MM-DD).",
    )
    parser_fetch.add_argument("--dry-run", dest="dry_run", action="store_true")

    options = parser.parse_args()
    kwargs = options.__dict__
    cmd = kwargs.pop("cmd")
    eval(cmd)(**kwargs)
