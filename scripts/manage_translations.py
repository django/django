#!/usr/bin/env python
"""
Django Translation Management Script.

This script provides utilities to manage Django translations, including:
- Updating translation catalogs (`update_catalogs`)
- Fetching translations from Transifex (`fetch`)
- Generating language statistics (`lang_stats`)

Usage:
    $ python scripts/manage_translations.py <command> [options]

Commands:
    update_catalogs  Update English .po files with new/updated strings
    lang_stats       Show translation statistics for each language
    fetch            Fetch translations from Transifex and compile .mo files

Options:
    -h, --help          Show help message
    -v, --verbosity     Set verbosity level (0-3)
    -r, --resources     Limit to specific resources (e.g., 'admin', 'gis')
    -l, --languages     Limit to specific languages (e.g., 'es', 'fr')
    -s, --since         Fetch translations updated after a date (YYYY-MM-DD)
"""

import json
import logging
import subprocess
from argparse import ArgumentParser
from collections import defaultdict
from configparser import ConfigParser
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import requests
import django
from django.conf import settings
from django.core.management import call_command

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Constants
HAVE_JS = ["admin"]
LANG_OVERRIDES = {
    "zh_CN": "zh_Hans",
    "zh_TW": "zh_Hant",
}
TRANSIFEX_API_URL = "https://rest.api.transifex.com"
TRANSIFEX_PROJECT = "o:django:p:django"


def run(
    *args: Union[str, List[str]],
    capture_output: bool = True,
    check: bool = True,
    text: bool = True,
    verbosity: int = 0,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Run a subprocess command safely."""
    if verbosity > 1:
        logger.debug(f"Running command: {args} {kwargs}")
    
    try:
        return subprocess.run(
            args,
            capture_output=capture_output,
            check=check,
            text=text,
            **kwargs,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        raise


def get_api_token() -> str:
    """Get Transifex API token from ENV or ~/.transifexrc."""
    api_token = os.getenv("TRANSIFEX_API_TOKEN")
    if not api_token:
        parser = ConfigParser()
        parser.read(Path.home() / ".transifexrc")
        api_token = parser.get("https://www.transifex.com", "token")
    
    if not api_token:
        raise ValueError("TRANSIFEX_API_TOKEN not found in ENV or ~/.transifexrc")
    return api_token


def get_api_response(
    endpoint: str,
    api_token: Optional[str] = None,
    params: Optional[Dict] = None,
    verbosity: int = 0,
) -> Dict:
    """Make a GET request to the Transifex API."""
    if api_token is None:
        api_token = get_api_token()
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/json",
    }
    
    url = f"{TRANSIFEX_API_URL}/{endpoint.strip('/')}"
    if verbosity > 2:
        logger.debug(f"GET {url} with params: {params}")
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    
    return response.json()["data"]


def list_resources_with_updates(
    date_since: datetime,
    resources: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    verbosity: int = 0,
) -> Dict[str, List[str]]:
    """List resources updated since a given date."""
    if verbosity:
        logger.info(f"Checking updates since {date_since.isoformat()}")
    
    if not languages:
        languages = [
            lang["attributes"]["code"]
            for lang in get_api_response(
                f"projects/{TRANSIFEX_PROJECT}/languages",
                verbosity=verbosity,
            )
        ]
    
    if not resources:
        resources = [
            res["attributes"]["slug"]
            for res in get_api_response(
                "resources",
                params={"filter[project]": TRANSIFEX_PROJECT},
                verbosity=verbosity,
            )
        ]
    else:
        resources = [_tx_resource_slug_for_name(r) for r in resources]
    
    resource_lang_changed = defaultdict(list)
    for lang, resource in product(languages, resources):
        if verbosity:
            logger.info(f"Checking {lang=} {resource=}")
        
        data = get_api_response(
            "resource_translations",
            params={
                "filter[resource]": f"{TRANSIFEX_PROJECT}:r:{resource}",
                "filter[language]": f"l:{lang}",
                "filter[date_translated][gt]": date_since.isoformat() + "Z",
            },
            verbosity=verbosity,
        )
        
        local_resource = resource.replace("contrib-", "", 1)
        local_lang = LANG_OVERRIDES.get(lang, lang)
        
        if data:
            resource_lang_changed[local_resource].append(local_lang)
    
    return resource_lang_changed


def _get_locale_dirs(
    resources: Optional[List[str]] = None,
    include_core: bool = True,
) -> List[Tuple[str, Path]]:
    """Return (resource_name, locale_dir) tuples."""
    base_dir = Path(__file__).parent.parent
    contrib_dir = base_dir / "django" / "contrib"
    dirs = []

    for contrib_name in contrib_dir.iterdir():
        locale_path = contrib_dir / contrib_name / "locale"
        if locale_path.is_dir():
            dirs.append((contrib_name, locale_path))
            if contrib_name in HAVE_JS:
                dirs.append((f"{contrib_name}-js", locale_path))
    
    if include_core:
        dirs.insert(0, ("core", base_dir / "django" / "conf" / "locale"))
    
    if resources:
        available = [d[0] for d in dirs]
        dirs = [d for d in dirs if d[0] in resources]
        if len(dirs) != len(resources):
            invalid = set(resources) - set(available)
            logger.error(f"Invalid resources: {invalid}. Available: {available}")
            raise ValueError("Invalid resources specified")
    
    return dirs


def _tx_resource_slug_for_name(name: str) -> str:
    """Convert resource name to Transifex slug (e.g., 'admin' → 'contrib-admin')."""
    return name if name == "core" else f"contrib-{name}"


def update_catalogs(
    resources: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    verbosity: int = 0,
) -> None:
    """Update English .po files with new translatable strings."""
    settings.configure()
    django.setup()
    
    if resources:
        logger.warning("`update_catalogs` always processes all resources.")
    
    os.chdir(Path(__file__).parent.parent / "django")
    
    logger.info("Updating en catalogs...")
    call_command("makemessages", locale=["en"], verbosity=verbosity)
    call_command("makemessages", locale=["en"], domain="djangojs", verbosity=verbosity)
    
    # Output stats
    core_path = Path("conf") / "locale"
    _check_diff("core", core_path)
    
    for name, dir_ in _get_locale_dirs(include_core=False):
        _check_diff(name, dir_)


def lang_stats(
    resources: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    verbosity: int = 0,
) -> None:
    """Print translation statistics for each language."""
    locale_dirs = _get_locale_dirs(resources)
    
    for name, dir_ in locale_dirs:
        logger.info(f"\nStats for '{name}':")
        langs = sorted(d for d in dir_.iterdir() if not d.name.startswith("_"))
        
        for lang in langs:
            if languages and lang.name not in languages:
                continue
            
            po_path = lang / "LC_MESSAGES" / f"django{'js' if name.endswith('-js') else ''}.po"
            result = run(
                ["msgfmt", "-vc", "-o", "/dev/null", str(po_path)],
                capture_output=True,
                verbosity=verbosity,
            )
            
            if result.returncode == 0:
                logger.info(f"{lang.name}: {result.stderr.strip()}")
            else:
                logger.error(f"Error checking {lang.name} for {name}:\n{result.stderr}")


def fetch(
    resources: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    date_since: Optional[datetime] = None,
    verbosity: int = 0,
) -> None:
    """Fetch translations from Transifex and compile .mo files."""
    if date_since:
        resource_lang_mapping = list_resources_with_updates(
            date_since, resources, languages, verbosity
        )
        resources = list(resource_lang_mapping.keys())
    
    locale_dirs = _get_locale_dirs(resources)
    errors = []
    
    for name, dir_ in locale_dirs:
        cmd = [
            "tx", "pull", "-r", _tx_resource_for_name(name),
            "-f", "--minimum-perc=5",
        ]
        
        langs = resource_lang_mapping.get(name, languages)
        if not langs:
            run([*cmd, "--all"], verbosity=verbosity)
            langs = [d.name for d in dir_.iterdir() if not d.name.startswith("_") and d.name != "en"]
        else:
            run([*cmd, "-l", ",".join(langs)], verbosity=verbosity)
        
        langs = [LANG_OVERRIDES.get(lang, lang) for lang in langs]
        
        for lang in langs:
            po_path = dir_ / lang / "LC_MESSAGES" / f"django{'js' if name.endswith('-js') else ''}.po"
            if not po_path.exists():
                logger.warning(f"No {lang} translation for {name}")
                continue
            
            run(["msgcat", "--no-location", "-o", str(po_path), str(po_path)], verbosity=verbosity)
            mo_path = po_path.with_suffix(".mo")
            
            result = run(
                ["msgfmt", "-c", "-o", str(mo_path), str(po_path)],
                verbosity=verbosity,
            )
            if result.returncode != 0:
                errors.append((name, lang))
    
    if errors:
        logger.error("\nErrors occurred:")
        for resource, lang in errors:
            logger.error(f"  - {resource} ({lang})")
        raise RuntimeError("Translation compilation failed")


def _check_diff(cat_name: str, base_path: Path) -> None:
    """Check for changes in the English catalog."""
    po_path = base_path / "en" / "LC_MESSAGES" / f"django{'js' if cat_name.endswith('-js') else ''}.po"
    result = run(
        f"git diff -U0 {po_path} | grep -E '^[-+]msgid' | wc -l",
        shell=True,
        capture_output=True,
    )
    changes = int(result.stdout.strip())
    logger.info(f"{changes} changes in '{cat_name}' catalog")


def _tx_resource_for_name(name: str) -> str:
    """Get full Transifex resource name (e.g., 'admin' → 'django.contrib-admin')."""
    return f"django.{_tx_resource_slug_for_name(name)}"


def main() -> None:
    """Parse CLI arguments and execute the command."""
    parser = ArgumentParser(description="Django Translation Management Tool")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    
    # Common arguments
    common_parser = ArgumentParser(add_help=False)
    common_parser.add_argument(
        "-r", "--resources", action="append", help="Limit to specific resources"
    )
    common_parser.add_argument(
        "-l", "--languages", action="append", help="Limit to specific languages"
    )
    common_parser.add_argument(
        "-v", "--verbosity", type=int, default=1, choices=[0, 1, 2, 3],
        help="Verbosity level (0=minimal, 3=debug)",
    )
    
    # Subcommands
    subparsers.add_parser("update_catalogs", parents=[common_parser])
    subparsers.add_parser("lang_stats", parents=[common_parser])
    
    fetch_parser = subparsers.add_parser("fetch", parents=[common_parser])
    fetch_parser.add_argument(
        "-s", "--since", type=datetime.fromisoformat,
        help="Fetch translations updated after YYYY-MM-DD",
    )
    
    args = parser.parse_args()
    kwargs = vars(args)
    cmd = kwargs.pop("cmd")
    
    try:
        globals()[cmd](**kwargs)
    except Exception as e:
        logger.error(f"Error in {cmd}: {e}", exc_info=args.verbosity > 1)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
