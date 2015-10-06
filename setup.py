"""
pip-review lets you smoothly manage all available PyPI updates.
"""
import sys
from setuptools import setup


def get_dependencies():
    deps = []
    if sys.version_info < (2, 7):
        deps += ['argparse']
    return deps


setup(
    name='pip-review',
    version='0.3.7',
    url='https://github.com/jgonggrijp/pip-review',
    license='BSD',
    author='Vincent Driessen, Julian Gonggrijp',
    author_email='j.gonggrijp@gmail.com',
    description=__doc__.strip('\n'),
    #packages=[],
    scripts=['bin/pip-review'],
    #include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=get_dependencies(),
    classifiers=[
        # As from https://pypi.python.org/pypi?%3Aaction=list_classifiers
        #'Development Status :: 1 - Planning',
        #'Development Status :: 2 - Pre-Alpha',
        #'Development Status :: 3 - Alpha',
        'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        #'Development Status :: 6 - Mature',
        #'Development Status :: 7 - Inactive',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        #'Programming Language :: Python :: 2.3',
        #'Programming Language :: Python :: 2.4',
        #'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        #'Programming Language :: Python :: 3',
        #'Programming Language :: Python :: 3.0',
        #'Programming Language :: Python :: 3.1',
        #'Programming Language :: Python :: 3.2',
        #'Programming Language :: Python :: 3.3',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: System :: Systems Administration',
    ]
)
