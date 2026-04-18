#! /bin/bash

# Verify a Django release: checks GPG signature, artifact checksums, and
# smoke-tests installation from both the tarball and the wheel.
#
# Usage: VERSION=5.2 bash scripts/verify_release.sh
#
# Set GPG_KEY to a key fingerprint to import it before verifying, e.g.:
#   GPG_KEY=<fingerprint> VERSION=5.2 bash scripts/verify_release.sh

set -xue

if [[ -z "${VERSION:-}" ]]; then
    echo "Please set VERSION as env var"
    exit 1
fi

if [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+(\.[0-9]+|a[0-9]+|b[0-9]+|rc[0-9]+)?$ ]]; then
    echo "Not a valid version"
    exit 1
fi

CHECKSUM_FILE="Django-${VERSION}.checksum.txt"
MEDIA_URL_PREFIX="https://media.djangoproject.com"
DOWNLOAD_PREFIX="https://www.djangoproject.com/download"

WORKDIR=$(mktemp -d)

function cleanup {
    rm -rf "${WORKDIR}"
}
trap cleanup EXIT

cd "${WORKDIR}"

echo "Downloading checksum file ..."
curl --fail --output "${CHECKSUM_FILE}" "${MEDIA_URL_PREFIX}/pgp/${CHECKSUM_FILE}"

echo "Verifying checksum file signature ..."
if [[ -n "${GPG_KEY:-}" ]]; then
    gpg --recv-keys "${GPG_KEY}"
fi
gpg --verify "${CHECKSUM_FILE}"

echo "Finding release artifacts ..."
mapfile -t RELEASE_ARTIFACTS < <(grep "${DOWNLOAD_PREFIX}" "${CHECKSUM_FILE}")

echo "Found these release artifacts:"
for ARTIFACT_URL in "${RELEASE_ARTIFACTS[@]}"; do
    echo "- ${ARTIFACT_URL}"
done

echo "Downloading artifacts ..."
for ARTIFACT_URL in "${RELEASE_ARTIFACTS[@]}"; do
    ARTIFACT_ACTUAL_URL=$(curl --head --write-out '%{redirect_url}' --output /dev/null --silent "${ARTIFACT_URL}")
    curl --location --fail --output "$(basename "${ARTIFACT_ACTUAL_URL}")" "${ARTIFACT_ACTUAL_URL}"
done

echo "Verifying artifact hashes ..."
# The `2>/dev/null` suppresses notes like "sha256sum: WARNING: 60 lines are
# improperly formatted". Return code is still set on error and a wrong
# checksum will still show up as FAILED.
echo "- MD5 checksums"
md5sum --check "${CHECKSUM_FILE}" 2>/dev/null
echo "- SHA1 checksums"
sha1sum --check "${CHECKSUM_FILE}" 2>/dev/null
echo "- SHA256 checksums"
sha256sum --check "${CHECKSUM_FILE}" 2>/dev/null

PKG_TAR=$(ls django-*.tar.gz)
PKG_WHL=$(ls django-*.whl)

echo "Testing tarball install ..."
python3 -m venv django-pip
. django-pip/bin/activate
python -m pip install --no-cache-dir "${WORKDIR}/${PKG_TAR}"
django-admin startproject test_tarball
cd test_tarball
./manage.py --help  # Ensure executable bits
python manage.py migrate
python manage.py runserver 0
deactivate
cd ..

echo "Testing wheel install ..."
python3 -m venv django-pip-wheel
. django-pip-wheel/bin/activate
python -m pip install --no-cache-dir "${WORKDIR}/${PKG_WHL}"
django-admin startproject test_wheel
cd test_wheel
./manage.py --help  # Ensure executable bits
python manage.py migrate
python manage.py runserver 0
deactivate
cd ..
