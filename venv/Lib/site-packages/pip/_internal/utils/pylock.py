from collections.abc import Iterable
from pathlib import Path

from pip._vendor.packaging.pylock import (
    Package,
    PackageArchive,
    PackageDirectory,
    PackageSdist,
    PackageVcs,
    PackageWheel,
    Pylock,
)
from pip._vendor.packaging.version import Version

from pip._internal.models.direct_url import ArchiveInfo, DirInfo, VcsInfo
from pip._internal.models.link import Link
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.urls import url_to_path


def _pylock_package_from_install_requirement(
    ireq: InstallRequirement, base_dir: Path
) -> Package:
    base_dir = base_dir.resolve()
    dist = ireq.get_dist()
    download_info = ireq.download_info
    assert download_info
    package_version = None
    package_vcs = None
    package_directory = None
    package_archive = None
    package_sdist = None
    package_wheels = None
    if ireq.is_direct:
        if isinstance(download_info.info, VcsInfo):
            package_vcs = PackageVcs(
                type=download_info.info.vcs,
                url=download_info.url,
                path=None,
                requested_revision=download_info.info.requested_revision,
                commit_id=download_info.info.commit_id,
                subdirectory=download_info.subdirectory,
            )
        elif isinstance(download_info.info, DirInfo):
            package_directory = PackageDirectory(
                path=(
                    Path(url_to_path(download_info.url))
                    .resolve()
                    .relative_to(base_dir)
                    .as_posix()
                ),
                editable=(
                    download_info.info.editable if download_info.info.editable else None
                ),
                subdirectory=download_info.subdirectory,
            )
        elif isinstance(download_info.info, ArchiveInfo):
            if not download_info.info.hashes:
                raise NotImplementedError()
            package_archive = PackageArchive(
                url=download_info.url,
                path=None,
                hashes=download_info.info.hashes,
                subdirectory=download_info.subdirectory,
            )
        else:
            # should never happen
            raise NotImplementedError()
    else:
        package_version = dist.version
        if isinstance(download_info.info, ArchiveInfo):
            if not download_info.info.hashes:
                raise NotImplementedError()
            link = Link(download_info.url)
            if link.is_wheel:
                package_wheels = [
                    PackageWheel(
                        name=link.filename,
                        url=download_info.url,
                        hashes=download_info.info.hashes,
                    )
                ]
            else:
                package_sdist = PackageSdist(
                    name=link.filename,
                    url=download_info.url,
                    hashes=download_info.info.hashes,
                )
        else:
            # should never happen
            raise NotImplementedError()
    return Package(
        name=dist.canonical_name,
        version=package_version,
        vcs=package_vcs,
        directory=package_directory,
        archive=package_archive,
        sdist=package_sdist,
        wheels=package_wheels,
    )


def pylock_from_install_requirements(
    install_requirements: Iterable[InstallRequirement], base_dir: Path
) -> Pylock:
    return Pylock(
        lock_version=Version("1.0"),
        created_by="pip",
        packages=sorted(
            (
                _pylock_package_from_install_requirement(ireq, base_dir)
                for ireq in install_requirements
            ),
            key=lambda p: p.name,
        ),
    )
