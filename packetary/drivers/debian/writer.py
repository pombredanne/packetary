#    Copyright 2015 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from __future__ import print_function

from contextlib import closing
import gzip
from itertools import groupby
import logging
import os.path
import six
import heapq

from debian import debfile

from packetary.drivers.debian.reader import load_packages
from packetary.objects.repository import Repository
from packetary.objects.package import Checksum
from packetary.objects.package import Package


logger = logging.getLogger(__package__)

_CHECKSUM_ORDER = (
    "MD5Sum",
    "SHA1",
    "SHA256"
)

_ARCHITECTURE_MAPPING = {
    "x86_64": "amd64",
    "i386": "i386",
    "source": "Source"
}


def save_packages(context, packages, keep_existing=True):
    """Saves the repository to disk."""

    groups = groupby(
        sorted(packages, key=lambda x: (x.repository, x)),
        key=lambda x: x.repository
    )
    with context.async_section() as section:
        for repo, packages in groups:
            section.execute(
                _save_package_in_repo, context, repo, packages, keep_existing
            )


def _save_package_in_repo(context, repo, packages, keep_existing):
    """Saves packages meta information in index-file."""
    local_path = _get_local_path(repo)
    arch = _ARCHITECTURE_MAPPING[repo.architecture]
    repo_dir = os.path.join(
        local_path, "dists", repo.name[0], repo.name[1],
        "binary-" + arch
    )
    try:
        os.makedirs(repo_dir)
    except OSError:
        pass

    index_name = os.path.join(repo_dir, "Packages")
    origin = "Origin: {0}\n".format(repo.origin).encode("utf8")

    existing = set()
    if os.path.exists(index_name + ".gz"):
        load_packages(context, repo_dir, existing.add)
        if keep_existing:
            packages = _drop_dublicates(
                heapq.merge(packages, sorted(existing))
            )

    with closing(open(index_name, "wb")) as index:
        with closing(gzip.open(index_name + ".gz", "wb")) as gzipped:
            writer = _composite_writer(index, gzipped)
            for p in packages:
                filename = os.path.join(local_path, p.filename)
                with closing(debfile.DebFile(filename)) as deb:
                    content = deb.control.get_content(debfile.CONTROL_FILE)
                    writer(content)
                    writer(origin)
                    writer("Size: {0}\n".format(p.size))
                    writer("Filename: {0}\n".format(p.filename))
                    for k, v in zip(_CHECKSUM_ORDER, p.checksum):
                        writer("{0}: {1}\n".format(k, v))
                    writer("\n")
                existing.discard(p)

    if not keep_existing:
        for p in keep_existing:
            os.remove(os.path.join(local_path, p.filename))
            logger.info("%s - removed.", p)

    _dumps_repository_meta(repo_dir, repo)


def _dumps_repository_meta(path, repo):
    """Writes the meta information for repository."""
    with closing(open(os.path.join(path, "Release"), "w")) as release:
        release.write(
            "Origin: {origin}\n"
            "Label: {name}\n"
            "Archive: {name}\n"
            "Architecture: {arch}\n"
            "Component: {component}\n"
            .format(
                origin=repo.origin,
                name=repo.name[0],
                component=repo.name[1],
                arch=_ARCHITECTURE_MAPPING[repo.architecture]
            )
        )


def _get_local_path(repository):
    url = repository.url
    if url.startswith("file://"):
        url = url[7:]
    if not url.startswith("/") or url.startswith("."):
        raise ValueError("Invalid URL: {0}".format(url))
    return url


def _composite_writer(*files):
    def write(s):
        if isinstance(s, six.text_type):
            s = s.encode("utf-8")
        for f in files:
            f.write(s)
    return write


def _drop_dublicates(seq):
    """Drops duplicates from sorted sequence."""
    it = iter(seq)
    p = next(it)
    yield p
    while True:
        n = next(it)
        if n != p:
            yield n
            p = n


def test():
    from packetary.context import Context

    ctx = Context()
    repo = Repository(name=("trusty", "updates"), architecture="x86_64",
                      url="/Users/bgaifullin/Sources/mirantis/fuel-mirror/mirror/ubuntu",
                      origin="Ubuntu")
    packages = [Package(name="aide", filename="pool/main/a/aide/aide_0.16~a2.git20130520-2ubuntu0.1_amd64.deb",
                        version="0.16~a2.git20130520-2ubuntu0", provides=[], requires=[], obsoletes=[],
                        repository=repo, checksum=Checksum(md5=123, sha1="qweq", sha256="asdfsfd"), size=10)]
    save_packages(ctx, packages)


if __name__ == "__main__":
    test()
