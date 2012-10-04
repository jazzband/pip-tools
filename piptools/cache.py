import os
import logging
#import shutil

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote  # noqa

from pip.backwardcompat import ConfigParser
from pip.locations import default_config_file
from pip.download import _download_url, _get_response_from_url

download_dir = os.path.join(os.path.expanduser('~'), '.pip-tools', 'cache')


def get_pip_cache_root():
    """Returns pip's cache root, or None if no such cache root is configured."""
    pip_config = ConfigParser.RawConfigParser()
    pip_config.read([default_config_file])
    download_cache = None
    try:
        for key, value in pip_config.items('global'):
            if key == 'download-cache':
                download_cache = value
                break
    except ConfigParser.NoSectionError:
        pass
    if download_cache is not None:
        download_cache = os.path.expanduser(download_cache)
    return download_cache


def get_local_package_path(url):
    """Returns the full local path name for a given URL.  This does not
    require the package to exist locally.  In fact, this can be used to
    calculate the destination path for a download.
    """
    cache_key = quote(url, '')
    fullpath = os.path.join(download_dir, cache_key)
    return fullpath


def download_package(link):
    """Downloads the given package link contents to the local package cache.
    Will overwrite anything that's in the cache already.
    """
    fullpath = get_local_package_path(link.url_fragment)

    # TODO: I've disabled this for now, let's first get it all working without
    # the extra cache layer
    #pip_cache_root = get_pip_cache_root()
    #if pip_cache_root:
    #    cache_path = os.path.join(pip_cache_root, cache_key)
    #    if os.path.exists(cache_path):
    #        # pip has a cached version, copy it
    #        shutil.copyfile(cache_path, fullpath)
    #
    #else:

    # actually download the requirement
    response = _get_response_from_url(link.url_fragment, link)
    _download_url(response, link, fullpath)

    return fullpath


def get_package_location(link):
    """Returns the package location for the given link.  Will try the local
    package cache first, then try to download it.
    """
    fullpath = get_local_package_path(link.url_fragment)

    if os.path.exists(fullpath):
        # package in local cache already
        logging.debug('Package in cache already.')
        return fullpath
    else:
        # requirement not cached, so download now
        logging.debug('Package not in cache, downloading...')
        return download_package(link)
