"""
pip-tools keeps your pinned dependencies fresh.
"""
from setuptools import find_packages, setup

setup(
    name='pip-tools',
    use_scm_version=True,
    url='https://github.com/jazzband/pip-tools/',
    license='BSD',
    author='Vincent Driessen',
    author_email='me@nvie.com',
    description=__doc__,
    packages=find_packages(exclude=['tests']),
    setup_requires=['setuptools_scm'],
    install_requires=[
        'click>=6',
        'first',
        'six',
        'setuptools'
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'pip-compile = piptools.scripts.compile:cli',
            'pip-sync = piptools.scripts.sync:cli',
        ],
    },
    platforms='any',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: System :: Systems Administration',
    ]
)
