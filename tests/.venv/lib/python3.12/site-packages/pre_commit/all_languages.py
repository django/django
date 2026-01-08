from __future__ import annotations

from pre_commit.lang_base import Language
from pre_commit.languages import conda
from pre_commit.languages import coursier
from pre_commit.languages import dart
from pre_commit.languages import docker
from pre_commit.languages import docker_image
from pre_commit.languages import dotnet
from pre_commit.languages import fail
from pre_commit.languages import golang
from pre_commit.languages import haskell
from pre_commit.languages import julia
from pre_commit.languages import lua
from pre_commit.languages import node
from pre_commit.languages import perl
from pre_commit.languages import pygrep
from pre_commit.languages import python
from pre_commit.languages import r
from pre_commit.languages import ruby
from pre_commit.languages import rust
from pre_commit.languages import swift
from pre_commit.languages import unsupported
from pre_commit.languages import unsupported_script


languages: dict[str, Language] = {
    'conda': conda,
    'coursier': coursier,
    'dart': dart,
    'docker': docker,
    'docker_image': docker_image,
    'dotnet': dotnet,
    'fail': fail,
    'golang': golang,
    'haskell': haskell,
    'julia': julia,
    'lua': lua,
    'node': node,
    'perl': perl,
    'pygrep': pygrep,
    'python': python,
    'r': r,
    'ruby': ruby,
    'rust': rust,
    'swift': swift,
    'unsupported': unsupported,
    'unsupported_script': unsupported_script,
}
language_names = sorted(languages)
