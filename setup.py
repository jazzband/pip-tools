"""
pip-tools keeps your pinned dependencies fresh.
"""
import sys
from setuptools import setup, find_packages


setup(
    name='pip-tools',
    version='1.0',
    url='https://github.com/nvie/pip-tools/',
    license='BSD',
    author='Vincent Driessen',
    author_email='vincent@3rdcloud.com',
    description=__doc__,
    packages=find_packages(),
    scripts=['bin/pip-compile', 'bin/pip-sync', 'bin/pip-review'],
    install_requires=['six'],
    #include_package_data=True,
    zip_safe=False,
    platforms='any',
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
        #'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        #'Programming Language :: Python :: 3.0',
        #'Programming Language :: Python :: 3.1',
        #'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: System :: Systems Administration',
    ]
)
