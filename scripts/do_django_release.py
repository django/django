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

checksum_file_text = """This file contains MD5, SHA1, and SHA256 checksums for the
source-code tarball and wheel files of Django {django_version}, released {release_date}.

It also includes the commit hash of the release tag, identifying the exact
source revision the artifacts were built from.

To use this file, you will need a working install of PGP or other
compatible public-key encryption software. You will also need to have
the Django release manager's public key in your keyring. This key has
the ID ``{pgp_key_id}`` and can be imported from GitHub, for example, if
using the open-source GNU Privacy Guard implementation of PGP:

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

Git tag
=======

The {django_version} tag points to commit {commit_hash}.
"""


def build_artifacts():
    from build.__main__ import main as build_main

    build_main([])


def do_checksum(checksum_algo, release_file, dist_path):
    with open(os.path.join(dist_path, release_file), "rb") as f:
        return checksum_algo(f.read()).hexdigest()


def get_commit_hash():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def parse_major_version(django_version):
    major = ".".join(django_version.split(".")[:2])
    match = re.search("[abrc]", major)
    if match:
        major = major[: match.start()]
    return major


def find_release_artifacts(dist_path):
    wheel_name = None
    tarball_name = None
    for f in os.listdir(dist_path):
        if f.endswith(".whl"):
            wheel_name = f
        elif f.endswith(".tar.gz"):
            tarball_name = f
    return wheel_name, tarball_name


def create_checksum_file(
    *,
    django_version,
    release_date,
    checksum_file_path,
    tarball_name,
    wheel_name,
    commit_hash,
    dist_path,
    pgp_key_id,
    pgp_key_url,
):
    kwargs = dict(
        release_date=release_date,
        pgp_key_id=pgp_key_id,
        django_version=django_version,
        pgp_key_url=pgp_key_url,
        checksum_file_name=os.path.basename(checksum_file_path),
        wheel_name=wheel_name,
        tarball_name=tarball_name,
        commit_hash=commit_hash,
    )
    for checksum_name, checksum_algo in (
        ("md5", hashlib.md5),
        ("sha1", hashlib.sha1),
        ("sha256", hashlib.sha256),
    ):
        kwargs[f"{checksum_name}_tarball"] = do_checksum(
            checksum_algo, tarball_name, dist_path
        )
        kwargs[f"{checksum_name}_wheel"] = do_checksum(
            checksum_algo, wheel_name, dist_path
        )
    with open(checksum_file_path, "wb") as f:
        f.write(checksum_file_text.format(**kwargs).encode("ascii"))


def main():
    pgp_key_id = os.getenv("PGP_KEY_ID")
    pgp_key_url = os.getenv("PGP_KEY_URL")
    pgp_email = os.getenv("PGP_EMAIL")
    dest_folder = os.path.expanduser(os.getenv("DEST_FOLDER"))

    assert (
        pgp_key_id
    ), "Missing PGP_KEY_ID: Set this env var to your PGP key ID (used for signing)."
    assert (
        pgp_key_url
    ), "Missing PGP_KEY_URL: Set this env var to your PGP public key URL."
    assert dest_folder and os.path.exists(
        dest_folder
    ), "Missing DEST_FOLDER: Set this env var to the path to place the artifacts."

    # Ensure the working directory is clean.
    subprocess.call(["git", "clean", "-fdx"])

    commit_hash = get_commit_hash()

    django_repo_path = os.path.abspath(os.path.curdir)
    dist_path = os.path.join(django_repo_path, "dist")

    # Build release files.
    build_artifacts()
    wheel_name, tarball_name = find_release_artifacts(dist_path)

    assert wheel_name is not None
    assert tarball_name is not None

    django_version = wheel_name.split("-")[1]
    django_major_version = parse_major_version(django_version)
    artifacts_path = os.path.join(dest_folder, django_version)
    os.makedirs(artifacts_path, exist_ok=True)
    release_date = date.today().strftime("%B %-d, %Y")
    checksum_file_path = os.path.join(
        artifacts_path, f"Django-{django_version}.checksum.txt"
    )

    create_checksum_file(
        django_version=django_version,
        release_date=release_date,
        checksum_file_path=checksum_file_path,
        wheel_name=wheel_name,
        tarball_name=tarball_name,
        commit_hash=commit_hash,
        dist_path=dist_path,
        pgp_key_id=pgp_key_id,
        pgp_key_url=pgp_key_url,
    )

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
    pgp_email_flag = f"-u {pgp_email} " if pgp_email else ""
    print(f"gpg --clearsign {pgp_email_flag}--digest-algo SHA256 {checksum_file_path}")
    # Create, verify and push tag.
    print(f'git tag --sign --message="Tag {django_version}" {django_version}')
    print(f"git tag --verify {django_version}")

    # Copy binaries outside the current repo tree to avoid lossing them.
    subprocess.run(["cp", "-r", dist_path, artifacts_path])

    # Make the binaries available to the world
    print(
        "\n\n=> These ONLY 15 MINUTES BEFORE RELEASE TIME (consider new terminal "
        "session with isolated venv)!"
    )

    # Upload the checksum file and artifacts to the djangoproject admin.
    print(
        "\n==> ACTION Add tarball, wheel, and checksum files to the Release entry at:"
        f"https://www.djangoproject.com/admin/releases/release/{django_version}"
    )
    print(
        f"* Tarball and wheel from {artifacts_path}\n"
        f"* Signed checksum {checksum_file_path}.asc"
    )

    # Verify the release artifacts (GPG signature, checksums, and smoke test).
    print("\n==> ACTION Verify the release artifacts:")
    print(f"VERSION={django_version} verify_release.sh")

    # Upload to PyPI.
    print("\n==> ACTION Upload to PyPI, ensure your release venv is activated:")
    print(f"cd {artifacts_path}")
    print("pip install -U pip twine")
    print("twine upload --repository django dist/*")

    # Push the tags.
    print("\n==> ACTION Push the tags:")
    print("git push --tags")

    print("\n\nDONE!!!")


if __name__ == "__main__":
    main()
