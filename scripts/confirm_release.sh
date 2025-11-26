#! /bin/bash

set -xue

CHECKSUM_FILE="Django-${VERSION}.checksum.txt"
MEDIA_URL_PREFIX="https://media.djangoproject.com"
RELEASE_URL_PREFIX="https://www.djangoproject.com/m/releases/"
DOWNLOAD_PREFIX="https://www.djangoproject.com/download"

if [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+(\.[0-9]+|a[0-9]+|b[0-9]+|rc[0-9]+)?$ ]] ; then
    echo "Not a valid version"
fi

rm -rf "${VERSION}"
mkdir "${VERSION}"
cd "${VERSION}"

function cleanup {
    cd ..
    rm -rf "${VERSION}"
}
trap cleanup EXIT

echo "Download checksum file ..."
curl --fail --output "$CHECKSUM_FILE" "${MEDIA_URL_PREFIX}/pgp/${CHECKSUM_FILE}"

echo "Verify checksum file ..."
if [ -n "${GPG_KEY:-}" ] ; then
    gpg --recv-keys "${GPG_KEY}"
fi
gpg --verify "${CHECKSUM_FILE}"

echo "Finding release artifacts ..."
mapfile -t RELEASE_ARTIFACTS < <(grep "${DOWNLOAD_PREFIX}" "${CHECKSUM_FILE}")

echo "Found these release artifacts: "
for ARTIFACT_URL in "${RELEASE_ARTIFACTS[@]}" ; do
    echo "- $ARTIFACT_URL"
done

echo "Downloading artifacts ..."
for ARTIFACT_URL in "${RELEASE_ARTIFACTS[@]}" ; do
    ARTIFACT_ACTUAL_URL=$(curl  --head --write-out '%{redirect_url}' --output /dev/null --silent "${ARTIFACT_URL}")
    curl --location --fail --output "$(basename "${ARTIFACT_ACTUAL_URL}")" "${ARTIFACT_ACTUAL_URL}"

done

echo "Verifying artifact hashes ..."
# The `2> /dev/null` moves notes like "sha256sum: WARNING: 60 lines are improperly formatted"
# to /dev/null. That's fine because the return code of the script is still set on error and a
# wrong checksum will still show up as `FAILED`
echo "- MD5 checksums"
md5sum --check "${CHECKSUM_FILE}" 2> /dev/null
echo "- SHA1 checksums"
sha1sum --check "${CHECKSUM_FILE}" 2> /dev/null
echo "- SHA256 checksums"
sha256sum --check "${CHECKSUM_FILE}" 2> /dev/null
