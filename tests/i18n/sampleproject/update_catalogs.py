#!/usr/bin/env python

"""
Helper script to update sampleproject's translation catalogs.

When a bug has been identified related to i18n, this helps capture the issue
by using catalogs created from management commands.

Example:

The string "Two %% Three %%%" renders differently using translate and
blocktranslate. This issue is difficult to debug, it could be a problem with
extraction, interpolation, or both.

How this script helps:
 * Add {% translate "Two %% Three %%%" %} and blocktranslate equivalent to templates.
 * Run this script.
 * Test extraction - verify the new msgid in sampleproject's django.po.
 * Add a translation to sampleproject's django.po.
 * Run this script.
 * Test interpolation - verify templatetag rendering, test each in a template
   that is rendered using an activated language from sampleproject's locale.
 * Tests should fail, issue captured.
 * Fix issue.
 * Run this script.
 * Tests all pass.
"""

import os
import re
import sys
from pathlib import Path

proj_dir = Path(__file__).parent
sys.path.append(str(proj_dir.parent.parent.parent))


def update_translation_catalogs():
    """Run makemessages and compilemessages in sampleproject."""
    from django.core.management import call_command

    prev_cwd = Path().cwd()

    os.chdir(proj_dir)
    call_command("makemessages")
    call_command("compilemessages")

    # keep the diff friendly - remove 'POT-Creation-Date'
    pofile = proj_dir / "locale" / "fr" / "LC_MESSAGES" / "django.po"

    content = pofile.read_text()
    content = re.sub(r'^"POT-Creation-Date.+$\s', "", content, flags=re.MULTILINE)
    pofile.write_text(content)

    os.chdir(prev_cwd)


if __name__ == "__main__":
    update_translation_catalogs()
