#!/usr/bin/env python
"""Script to help compare releases on PyPI.

It creates a git repo and creates a commit for each release on PyPI. It
requires these packages to be installed:
GitPython
requests
"""

import tarfile
import io
import os
import os.path
import shutil
import requests
import git


_pypi_response = None

def _get_pypi_response():
    global _pypi_response
    if _pypi_response is None:
        resp = requests.get("https://pypi.python.org/pypi/EVE-SRP/json")
        _pypi_response = resp.json()
    return _pypi_response


def get_evesrp_url(version):
    resp = _get_pypi_response()
    release_info = resp[u'releases'][version]
    for release in release_info:
        if release[u'packagetype'] == 'sdist':
            return release[u'url']
    return release_info[0][u'url']


def get_evesrp_versions():
    resp = _get_pypi_response()
    versions = resp[u'releases'].keys()
    versions = list(versions)
    versions.sort(key=lambda v: map(int, v.split('.')))
    return versions


def extract_source(version):
    # Clean out the staging directory
    try:
        shutil.rmtree('./evesrp')
    except OSError:
        pass
    os.mkdir('./evesrp')
    # Get the tarball data and extract those 
    tarball_url = get_evesrp_url(version)
    resp = requests.get(tarball_url)
    io_buffer = io.BytesIO(resp.content)
    tarball = tarfile.open(fileobj=io_buffer)
    evesrp_prefix = None
    for tarinfo in tarball:
        if os.path.basename(tarinfo.name) == 'evesrp':
            evesrp_prefix = tarinfo.name
        elif evesrp_prefix is not None and \
                tarinfo.name.startswith(evesrp_prefix):
            tarball.extract(tarinfo)
    os.rename(evesrp_prefix, './evesrp')
    shutil.rmtree(os.path.dirname(evesrp_prefix))


def create_repo():
    basepath = os.path.abspath('.')
    evesrp_path = os.path.join(basepath, 'evesrp')
    repo = git.Repo.init(basepath)
    for version in get_evesrp_versions():
        extract_source(version)
        repo.index.add([evesrp_path])
        repo.index.commit('v{}'.format(version))


if __name__ == '__main__':
    create_repo()
