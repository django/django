#! /usr/bin/env python

"""Helper to build and publish Django artifacts.

Original author: Tim Graham.
Other authors: Mariusz Felisiak, Natalia Bidart.

"""

import hashlib
import os
import re
import subprocess
from datetime import date

PGP_KEY_ID = os.getenv("PGP_KEY_ID")
PGP_KEY_URL = os.getenv("PGP_KEY_URL")
PGP_EMAIL = os.getenv("PGP_EMAIL")
DEST_FOLDER = os.path.expanduser(os.getenv("DEST_FOLDER"))

assert (
    PGP_KEY_ID
), "Missing PGP_KEY_ID: Set this env var to your PGP key ID (used for signing)."
assert (
    PGP_KEY_URL
), "Missing PGP_KEY_URL: Set this env var to your PGP public key URL (for fetching)."
assert DEST_FOLDER and os.path.exists(
    DEST_FOLDER
), "Missing DEST_FOLDER: Set this env var to the local path to place the artifacts."


checksum_file_text = """This file contains MD5, SHA1, and SHA256 checksums for the
source-code tarball and wheel files of Django {django_version}, released {release_date}.

To use this file, you will need a working install of PGP or other
compatible public-key encryption software. You will also need to have
the Django release manager's public key in your keyring. This key has
the ID ``{pgp_key_id}`` and can be imported from the MIT
keyserver, for example, if using the open-source GNU Privacy Guard
implementation of PGP:

    gpg --keyserver pgp.mit.edu --recv-key {pgp_key_id}

or via the GitHub API:

    curl {pgp_key_url} | gpg --import -

Once the key is imported, verify this file:

    gpg --verify {checksum_file_name}

Once you have verified this file, you can use normal MD5, SHA1, or SHA256
checksumming applications to generate the checksums of the Django
package and compare them to the checksums listed below.

Release packages
================

https://www.djangoproject.com/download/{django_version}/tarball/
https://www.djangoproject.com/download/{django_version}/wheel/

MD5 checksums
=============

{md5_tarball}  {tarball_name}
{md5_wheel}  {wheel_name}

SHA1 checksums
==============

{sha1_tarball}  {tarball_name}
{sha1_wheel}  {wheel_name}

SHA256 checksums
================

{sha256_tarball}  {tarball_name}
{sha256_wheel}  {wheel_name}

"""


def build_artifacts():
    from build.__main__ import main as build_main

    build_main([])


def do_checksum(checksum_algo, release_file):
    with open(os.path.join(dist_path, release_file), "rb") as f:
        return checksum_algo(f.read()).hexdigest()


# Ensure the working directory is clean.
subprocess.call(["git", "clean", "-fdx"])

django_repo_path = os.path.abspath(os.path.curdir)
dist_path = os.path.join(django_repo_path, "dist")

# Build release files.
build_artifacts()
release_files = os.listdir(dist_path)
wheel_name = None
tarball_name = None
for f in release_files:
    if f.endswith(".whl"):
        wheel_name = f
    if f.endswith(".tar.gz"):
        tarball_name = f

assert wheel_name is not None
assert tarball_name is not None

django_version = wheel_name.split("-")[1]
django_major_version = ".".join(django_version.split(".")[:2])

artifacts_path = os.path.join(os.path.expanduser(DEST_FOLDER), django_version)
os.makedirs(artifacts_path, exist_ok=True)

# Chop alpha/beta/rc suffix
match = re.search("[abrc]", django_major_version)
if match:
    django_major_version = django_major_version[: match.start()]

release_date = date.today().strftime("%B %-d, %Y")
checksum_file_name = f"Django-{django_version}.checksum.txt"
checksum_file_kwargs = dict(
    release_date=release_date,
    pgp_key_id=PGP_KEY_ID,
    django_version=django_version,
    pgp_key_url=PGP_KEY_URL,
    checksum_file_name=checksum_file_name,
    wheel_name=wheel_name,
    tarball_name=tarball_name,
)
checksums = (
    ("md5", hashlib.md5),
    ("sha1", hashlib.sha1),
    ("sha256", hashlib.sha256),
)
for checksum_name, checksum_algo in checksums:
    checksum_file_kwargs[f"{checksum_name}_tarball"] = do_checksum(
        checksum_algo, tarball_name
    )
    checksum_file_kwargs[f"{checksum_name}_wheel"] = do_checksum(
        checksum_algo, wheel_name
    )

# Create the checksum file
checksum_file_text = checksum_file_text.format(**checksum_file_kwargs)
checksum_file_path = os.path.join(artifacts_path, checksum_file_name)
with open(checksum_file_path, "wb") as f:
    f.write(checksum_file_text.encode("ascii"))

print("\n\nDiffing release with checkout for sanity check.")

# Unzip and diff...
unzip_command = [
    "unzip",
    "-q",
    os.path.join(dist_path, wheel_name),
    "-d",
    os.path.join(dist_path, django_major_version),
]
subprocess.run(unzip_command)
diff_command = [
    "diff",
    "-qr",
    "./django/",
    os.path.join(dist_path, django_major_version, "django"),
]
subprocess.run(diff_command)
subprocess.run(
    [
        "rm",
        "-rf",
        os.path.join(dist_path, django_major_version),
    ]
)

print("\n\n=> Commands to run NOW:")

# Sign the checksum file, this may prompt for a passphrase.
pgp_email = f"-u {PGP_EMAIL} " if PGP_EMAIL else ""
print(f"gpg --clearsign {pgp_email}--digest-algo SHA256 {checksum_file_path}")
# Create, verify and push tag
print(f'git tag --sign --message="Tag {django_version}" {django_version}')
print(f"git tag --verify {django_version}")

# Copy binaries outside the current repo tree to avoid lossing them.
subprocess.run(["cp", "-r", dist_path, artifacts_path])

# Make the binaries available to the world
print(
    "\n\n=> These ONLY 15 MINUTES BEFORE RELEASE TIME (consider new terminal "
    "session with isolated venv)!"
)

# Upload the checksum file and release artifacts to the djangoproject admin.
print(
    "\n==> ACTION Add tarball, wheel, and checksum files to the Release entry at:"
    f"https://www.djangoproject.com/admin/releases/release/{django_version}"
)
print(
    f"* Tarball and wheel from {artifacts_path}\n"
    f"* Signed checksum {checksum_file_path}.asc"
)

# Test the new version and confirm the signature using Jenkins.
print("\n==> ACTION Test the release artifacts:")
print(f"VERSION={django_version} test_new_version.sh")

print("\n==> ACTION Run confirm-release job:")
print(f"VERSION={django_version} confirm_release.sh")

# Upload to PyPI.
print("\n==> ACTION Upload to PyPI, ensure your release venv is activated:")
print(f"cd {artifacts_path}")
print("pip install -U pip twine")
print("twine upload --repository django dist/*")

# Push the tags.
print("\n==> ACTION Push the tags:")
print("git push --tags")

print("\n\nDONE!!!")
