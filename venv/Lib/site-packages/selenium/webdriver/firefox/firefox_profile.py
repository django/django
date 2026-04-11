# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import base64
import copy
import json
import os
import re
import shutil
import sys
import tempfile
import warnings
import zipfile
from io import BytesIO
from xml.dom import minidom

from typing_extensions import deprecated

from selenium.common.exceptions import WebDriverException

WEBDRIVER_PREFERENCES = "webdriver_prefs.json"


@deprecated("Addons must be added after starting the session")
class AddonFormatError(Exception):
    """Exception for not well-formed add-on manifest files."""


class FirefoxProfile:
    DEFAULT_PREFERENCES = None

    def __init__(self, profile_directory=None):
        """Initialises a new instance of a Firefox Profile.

        Args:
            profile_directory: Directory of profile that you want to use. If a
                directory is passed in it will be cloned and the cloned directory
                will be used by the driver when instantiated.
                This defaults to None and will create a new
                directory when object is created.
        """
        self._desired_preferences = {}
        if profile_directory:
            newprof = os.path.join(tempfile.mkdtemp(), "webdriver-py-profilecopy")
            shutil.copytree(
                profile_directory, newprof, ignore=shutil.ignore_patterns("parent.lock", "lock", ".parentlock")
            )
            self._profile_dir = newprof
            os.chmod(self._profile_dir, 0o755)
        else:
            self._profile_dir = tempfile.mkdtemp()
            if not FirefoxProfile.DEFAULT_PREFERENCES:
                with open(
                    os.path.join(os.path.dirname(__file__), WEBDRIVER_PREFERENCES), encoding="utf-8"
                ) as default_prefs:
                    FirefoxProfile.DEFAULT_PREFERENCES = json.load(default_prefs)

            self._desired_preferences = copy.deepcopy(FirefoxProfile.DEFAULT_PREFERENCES["mutable"])
            for key, value in FirefoxProfile.DEFAULT_PREFERENCES["frozen"].items():
                self._desired_preferences[key] = value

    # Public Methods
    def set_preference(self, key, value):
        """Sets the preference that we want in the profile."""
        self._desired_preferences[key] = value

    @deprecated("Addons must be added after starting the session")
    def add_extension(self, extension=None):
        self._install_extension(extension)

    def update_preferences(self):
        """Writes the desired user prefs to disk."""
        user_prefs = os.path.join(self._profile_dir, "user.js")
        if os.path.isfile(user_prefs):
            os.chmod(user_prefs, 0o644)
            self._read_existing_userjs(user_prefs)
        with open(user_prefs, "w", encoding="utf-8") as f:
            for key, value in self._desired_preferences.items():
                f.write(f'user_pref("{key}", {json.dumps(value)});\n')

    # Properties

    @property
    def path(self):
        """Gets the profile directory that is currently being used."""
        return self._profile_dir

    @property
    @deprecated("The port is stored in the Service class")
    def port(self):
        """Gets the port that WebDriver is working on."""
        return self._port

    @port.setter
    @deprecated("The port is stored in the Service class")
    def port(self, port) -> None:
        """Sets the port that WebDriver will be running on."""
        if not isinstance(port, int):
            raise WebDriverException("Port needs to be an integer")
        try:
            port = int(port)
            if port < 1 or port > 65535:
                raise WebDriverException("Port number must be in the range 1..65535")
        except (ValueError, TypeError):
            raise WebDriverException("Port needs to be an integer")
        self._port = port
        self.set_preference("webdriver_firefox_port", self._port)

    @property
    @deprecated("Allowing untrusted certs is toggled in the Options class")
    def accept_untrusted_certs(self):
        return self._desired_preferences["webdriver_accept_untrusted_certs"]

    @accept_untrusted_certs.setter
    @deprecated("Allowing untrusted certs is toggled in the Options class")
    def accept_untrusted_certs(self, value) -> None:
        if not isinstance(value, bool):
            raise WebDriverException("Please pass in a Boolean to this call")
        self.set_preference("webdriver_accept_untrusted_certs", value)

    @property
    @deprecated("Allowing untrusted certs is toggled in the Options class")
    def assume_untrusted_cert_issuer(self):
        return self._desired_preferences["webdriver_assume_untrusted_issuer"]

    @assume_untrusted_cert_issuer.setter
    @deprecated("Allowing untrusted certs is toggled in the Options class")
    def assume_untrusted_cert_issuer(self, value) -> None:
        if not isinstance(value, bool):
            raise WebDriverException("Please pass in a Boolean to this call")

        self.set_preference("webdriver_assume_untrusted_issuer", value)

    @property
    def encoded(self) -> str:
        """Update preferences and create a zipped, base64-encoded profile directory string."""
        if self._desired_preferences:
            self.update_preferences()
        fp = BytesIO()
        with zipfile.ZipFile(fp, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as zipped:
            path_root = len(self.path) + 1  # account for trailing slash
            for base, _, files in os.walk(self.path):
                for fyle in files:
                    filename = os.path.join(base, fyle)
                    zipped.write(filename, filename[path_root:])
        return base64.b64encode(fp.getvalue()).decode("UTF-8")

    def _read_existing_userjs(self, userjs):
        """Read existing preferences and add them to the desired preference dictionary."""
        pref_pattern = re.compile(r'user_pref\("(.*)",\s(.*)\)')
        with open(userjs, encoding="utf-8") as f:
            for usr in f:
                matches = pref_pattern.search(usr)
                try:
                    self._desired_preferences[matches.group(1)] = json.loads(matches.group(2))
                except Exception:
                    warnings.warn(
                        f"(skipping) failed to json.loads existing preference: {matches.group(1) + matches.group(2)}"
                    )

    @deprecated("Addons must be added after starting the session")
    def _install_extension(self, addon, unpack=True):
        """Install addon from a filepath, URL, or directory of addons in the profile.

        Args:
            addon: url, absolute path to .xpi, or directory of addons
            unpack: whether to unpack unless specified otherwise in the install.rdf
        """
        tmpdir = None
        xpifile = None
        if addon.endswith(".xpi"):
            tmpdir = tempfile.mkdtemp(suffix="." + os.path.split(addon)[-1])
            compressed_file = zipfile.ZipFile(addon, "r")
            for name in compressed_file.namelist():
                if name.endswith("/"):
                    if not os.path.isdir(os.path.join(tmpdir, name)):
                        os.makedirs(os.path.join(tmpdir, name))
                else:
                    if not os.path.isdir(os.path.dirname(os.path.join(tmpdir, name))):
                        os.makedirs(os.path.dirname(os.path.join(tmpdir, name)))
                    data = compressed_file.read(name)
                    with open(os.path.join(tmpdir, name), "wb") as f:
                        f.write(data)
            xpifile = addon
            addon = tmpdir

        # determine the addon id
        addon_details = self._addon_details(addon)
        addon_id = addon_details.get("id")
        assert addon_id, f"The addon id could not be found: {addon}"

        # copy the addon to the profile
        extensions_dir = os.path.join(self._profile_dir, "extensions")
        addon_path = os.path.join(extensions_dir, addon_id)
        if not unpack and not addon_details["unpack"] and xpifile:
            if not os.path.exists(extensions_dir):
                os.makedirs(extensions_dir)
                os.chmod(extensions_dir, 0o755)
            shutil.copy(xpifile, addon_path + ".xpi")
        else:
            if not os.path.exists(addon_path):
                shutil.copytree(addon, addon_path, symlinks=True)

        # remove the temporary directory, if any
        if tmpdir:
            shutil.rmtree(tmpdir)

    @deprecated("Addons must be added after starting the session")
    def _addon_details(self, addon_path):
        """Returns a dictionary of details about the addon.

        Args:
            addon_path: path to the add-on directory or XPI

        Returns:
            A dictionary containing:

            {
                "id": "rainbow@colors.org",  # id of the addon
                "version": "1.4",  # version of the addon
                "name": "Rainbow",  # name of the addon
                "unpack": False,
            }  # whether to unpack the addon
        """
        details = {"id": None, "unpack": False, "name": None, "version": None}

        def get_namespace_id(doc, url):
            attributes = doc.documentElement.attributes
            namespace = ""
            for i in range(attributes.length):
                if attributes.item(i).value == url:
                    if ":" in attributes.item(i).name:
                        # If the namespace is not the default one remove 'xlmns:'
                        namespace = attributes.item(i).name.split(":")[1] + ":"
                        break
            return namespace

        def get_text(element):
            """Retrieve the text value of a given node."""
            rc = []
            for node in element.childNodes:
                if node.nodeType == node.TEXT_NODE:
                    rc.append(node.data)
            return "".join(rc).strip()

        def parse_manifest_json(content):
            """Extract details from the contents of a WebExtensions manifest.json file."""
            manifest = json.loads(content)
            try:
                id = manifest["applications"]["gecko"]["id"]
            except KeyError:
                id = manifest["name"].replace(" ", "") + "@" + manifest["version"]
            return {
                "id": id,
                "version": manifest["version"],
                "name": manifest["version"],
                "unpack": False,
            }

        if not os.path.exists(addon_path):
            raise OSError(f"Add-on path does not exist: {addon_path}")

        try:
            if zipfile.is_zipfile(addon_path):
                with zipfile.ZipFile(addon_path, "r") as compressed_file:
                    if "manifest.json" in compressed_file.namelist():
                        return parse_manifest_json(compressed_file.read("manifest.json"))

                    manifest = compressed_file.read("install.rdf")
            elif os.path.isdir(addon_path):
                manifest_json_filename = os.path.join(addon_path, "manifest.json")
                if os.path.exists(manifest_json_filename):
                    with open(manifest_json_filename, encoding="utf-8") as f:
                        return parse_manifest_json(f.read())

                with open(os.path.join(addon_path, "install.rdf"), encoding="utf-8") as f:
                    manifest = f.read()
            else:
                raise OSError(f"Add-on path is neither an XPI nor a directory: {addon_path}")
        except (OSError, KeyError) as e:
            raise AddonFormatError(str(e), sys.exc_info()[2])

        try:
            doc = minidom.parseString(manifest)

            # Get the namespaces abbreviations
            em = get_namespace_id(doc, "http://www.mozilla.org/2004/em-rdf#")
            rdf = get_namespace_id(doc, "http://www.w3.org/1999/02/22-rdf-syntax-ns#")

            description = doc.getElementsByTagName(rdf + "Description").item(0)
            if not description:
                description = doc.getElementsByTagName("Description").item(0)
            for node in description.childNodes:
                # Remove the namespace prefix from the tag for comparison
                entry = node.nodeName.replace(em, "")
                if entry in details:
                    details.update({entry: get_text(node)})
            if not details.get("id"):
                for i in range(description.attributes.length):
                    attribute = description.attributes.item(i)
                    if attribute.name == em + "id":
                        details.update({"id": attribute.value})
        except Exception as e:
            raise AddonFormatError(str(e), sys.exc_info()[2])

        # turn unpack into a true/false value
        if isinstance(details["unpack"], str):
            details["unpack"] = details["unpack"].lower() == "true"

        # If no ID is set, the add-on is invalid
        if not details.get("id"):
            raise AddonFormatError("Add-on id could not be found.")

        return details
