from functools import partial
import subprocess
import requests
import multiprocessing
import json


def get_pkg_info(pkg_name, session):
    r = session.get('http://pypi.python.org/pypi/%s/json' % (pkg_name,))
    if r.status_code == requests.codes.ok:
        return json.loads(r.text)
    else:
        raise ValueError('Package %r not found on PyPI.' % (pkg_name,))


def latest_version(pkg_name, session, silent=False):
    try:
        info = get_pkg_info(pkg_name, session)
    except ValueError:
        if silent:
            return None
        else:
            raise
    return info['info']['version']


def get_latest_versions(pkg_names):
    with requests.session() as session:
        pool = multiprocessing.Pool(min(12, len(pkg_names)))
        get_latest = partial(latest_version, session=session, silent=True)
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
