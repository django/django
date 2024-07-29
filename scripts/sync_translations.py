import os
from argparse import ArgumentParser
from collections import defaultdict
from configparser import ConfigParser
from datetime import datetime

import requests
from manage_translations import fetch


def list_resources_with_updates(date_since, verbose=False):
    resource_lang_changed = defaultdict(list)
    resource_lang_unchanged = defaultdict(list)

    # Read token from ENV, otherwsie read from the ~/.transifexrc file.
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
            last_update = lang_data["attributes"]["last_translation_update"]
            if verbose:
                print(
                    f"CHECKING {resource_name} for {lang_id=} updated on {last_update}"
                )
            if last_update is None:
                resource_lang_unchanged[resource_name].append(lang_id)
                continue

            last_update = datetime.strptime(last_update, "%Y-%m-%dT%H:%M:%SZ")
            if last_update > date_since:
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


def fetch_since(date_since, verbose=True, dry_run=True):
    changed = list_resources_with_updates(date_since=date_since, verbose=verbose)
    if verbose:
        print(f"== SUMMARY for changed resources {dry_run=} ==\n")
    for res, langs in changed.items():
        if verbose:
            print(f"\n * resource {res} languages {' '.join(sorted(langs))}")
        if not dry_run:
            fetch(resources=[res], languages=sorted(langs))
    if not changed and verbose:
        print(f"\n No resource changed since {date_since}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument(
        "-d",
        "--date-since",
        dest="date_since",
        metavar="YYYY-MM-DD",
        type=datetime.fromisoformat,
        help="Fetch new translations since this date (ISO format YYYY-MM-DD).",
    )
    options = parser.parse_args()
    fetch_since(**options.__dict__)
