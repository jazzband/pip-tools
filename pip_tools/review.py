from functools import partial
import subprocess
import urllib2
import multiprocessing
import json
import logging


def get_pkg_info(pkg_name):
    logging.debug('Checking for updates of %r' % (pkg_name,))
    req = urllib2.Request('http://pypi.python.org/pypi/%s/json' % (pkg_name,))
    handler = urllib2.urlopen(req)
    status = handler.getcode()
    if status == 200:
        content = handler.read()
        return json.loads(content)
    else:
        raise ValueError('Package %r not found on PyPI.' % (pkg_name,))


def latest_version(pkg_name, silent=False):
    try:
        info = get_pkg_info(pkg_name)
    except ValueError:
        if silent:
            return None
        else:
            raise
    return info['info']['version']


def get_latest_versions(pkg_names):
    pool = multiprocessing.Pool(min(12, len(pkg_names)))
    get_latest = partial(latest_version, silent=True)
    versions = pool.map(get_latest, pkg_names)
    return zip(pkg_names, versions)


def get_installed_pkgs(editables=False):
    for line in subprocess.check_output(['pip', 'freeze']).split('\n'):
        if not line:
            continue

        if line.startswith('-e'):
            if editables:
                yield line.split('#egg=', 1)[1], None, True
        else:
            name, version = line.split('==')
            yield name, version, False
