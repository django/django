from __future__ import annotations

from pathlib import Path

from virtualenv.seed.wheels.util import Wheel

BUNDLE_FOLDER = Path(__file__).absolute().parent
BUNDLE_SUPPORT = {
    "3.8": {
        "pip": "pip-25.0.1-py3-none-any.whl",
        "setuptools": "setuptools-75.3.2-py3-none-any.whl",
        "wheel": "wheel-0.45.1-py3-none-any.whl",
    },
    "3.9": {
        "pip": "pip-25.3-py3-none-any.whl",
        "setuptools": "setuptools-80.9.0-py3-none-any.whl",
    },
    "3.10": {
        "pip": "pip-25.3-py3-none-any.whl",
        "setuptools": "setuptools-80.9.0-py3-none-any.whl",
    },
    "3.11": {
        "pip": "pip-25.3-py3-none-any.whl",
        "setuptools": "setuptools-80.9.0-py3-none-any.whl",
    },
    "3.12": {
        "pip": "pip-25.3-py3-none-any.whl",
        "setuptools": "setuptools-80.9.0-py3-none-any.whl",
    },
    "3.13": {
        "pip": "pip-25.3-py3-none-any.whl",
        "setuptools": "setuptools-80.9.0-py3-none-any.whl",
    },
    "3.14": {
        "pip": "pip-25.3-py3-none-any.whl",
        "setuptools": "setuptools-80.9.0-py3-none-any.whl",
    },
    "3.15": {
        "pip": "pip-25.3-py3-none-any.whl",
        "setuptools": "setuptools-80.9.0-py3-none-any.whl",
    },
}
MAX = "3.8"


def get_embed_wheel(distribution, for_py_version):
    mapping = BUNDLE_SUPPORT.get(for_py_version, {}) or BUNDLE_SUPPORT[MAX]
    wheel_file = mapping.get(distribution)
    if wheel_file is None:
        return None
    path = BUNDLE_FOLDER / wheel_file
    return Wheel.from_path(path)


__all__ = [
    "BUNDLE_FOLDER",
    "BUNDLE_SUPPORT",
    "MAX",
    "get_embed_wheel",
]
