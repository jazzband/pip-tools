import click
from pip._vendor.packaging.version import Version

CLICK_VERSION = Version(click.__version__).major
IS_CLICK_VER_8_PLUS = CLICK_VERSION > 7
