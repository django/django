"""Utilities for pre-parsing GeoJSON inputs before forwarding to GDAL."""

import json

from django.core.exceptions import SuspiciousOperation
from django.utils.regex_helper import _lazy_re_compile


class ExternalCRSBlocker:
    """
    Reject any GeoJSON CRS that would make GDAL fetch or read a file.

    The only CRS references accepted are those OGRSpatialReference resolves
    against the local PROJ database without I/O: an ``AUTHORITY:CODE`` from a
    known authority, an OGC CRS URN, or a well-known shorthand e.g. ``CRS84``.
    """

    AUTHORITIES = frozenset(
        {
            "epsg",
            "epsga",
            "esri",
            "ogc",
            "iau",
            "iau2000",
            "iau_2015",
            "ignf",
            "mysql",
            "nkg",
            "nrcan",
            "proj",
        }
    )
    # AUTHORITY:CODE with exactly one colon, e.g. EPSG:4326, OGC:CRS84.
    AUTHORITY_CODE = _lazy_re_compile(r"([A-Za-z][A-Za-z0-9_]*):([0-9A-Za-z]+)\Z")
    # OGC CRS URN, e.g. urn:ogc:def:crs:EPSG::4326.
    OGC_URN = _lazy_re_compile(
        r"urn:ogc:def:crs:[A-Za-z0-9_]+:[0-9A-Za-z.]*:[0-9A-Za-z]+\Z"
    )
    # Bare shorthands that carry no authority prefix.
    BARE = frozenset({"crs84", "crs27", "crs83", "wgs84"})

    @classmethod
    def check(cls, value):
        value_dict = json.loads(value)
        if not isinstance(value_dict, dict):
            raise ValueError("GeoJSON geometry must be an object.")

        # Keep iterators rather than a list of pending geometries so that wide
        # collections don't require extra space proportional to their size.
        members = [iter(value_dict.items())]
        while members:
            try:
                key, member = next(members[-1])
            except StopIteration:
                members.pop()
                continue
            # GDAL compares member names case-insensitively as C strings.
            key = key.split("\0", 1)[0].lower()
            if key == "crs":
                if member is None:
                    continue
                if not isinstance(member, dict):
                    raise ValueError("GeoJSON CRS must be an object.")
                cls.check_member(member)
            elif key == "geometries" and isinstance(member, list):
                # Follow collection members, not coordinates or properties.
                members.append(
                    (
                        item
                        for geometry in member
                        if isinstance(geometry, dict)
                        for item in geometry.items()
                    )
                )
            elif key == "geometry" and isinstance(member, dict):
                members.append(iter(member.items()))

    @staticmethod
    def normalize_key(key):
        return key.split("\0", 1)[0].lower()

    @classmethod
    def check_member(cls, member):
        crs_type_values = []
        crs_properties_values = []
        for crs_key, crs_value in member.items():
            normalized_key = cls.normalize_key(crs_key)
            if normalized_key == "type":
                crs_type_values.append(crs_value)
            elif normalized_key == "properties":
                crs_properties_values.append(crs_value)
        for crs_type in crs_type_values:
            if isinstance(crs_type, str) and crs_type.lower().startswith(
                ("link", "url")
            ):
                raise SuspiciousOperation("GeoJSON input specified an external CRS.")
        for crs_properties in crs_properties_values:
            if isinstance(crs_properties, dict):
                for prop_key, prop_value in crs_properties.items():
                    normalized_prop_key = cls.normalize_key(prop_key)
                    if normalized_prop_key == "name":
                        cls.check_crs_name(prop_value)

    @classmethod
    def check_crs_name(cls, name):
        if not isinstance(name, str):
            raise ValueError("GeoJSON CRS name must be a string.")
        if "\0" in name:
            raise ValueError("GeoJSON CRS name must not contain null characters.")

        # SetFromUserInput() skips leading whitespace, so strip first.
        candidate = name.strip().lower()
        match = cls.AUTHORITY_CODE.match(candidate)
        if match and match.group(1) in cls.AUTHORITIES:
            return
        if cls.OGC_URN.match(candidate):
            return
        if candidate in cls.BARE:
            return

        raise SuspiciousOperation("GeoJSON input specified an external CRS.")
