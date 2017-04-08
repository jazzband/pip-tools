.. image:: https://travis-ci.org/jgonggrijp/pip-review.svg?branch=master
    :alt: Build status
    :target: https://secure.travis-ci.org/jgonggrijp/pip-review

pip-review
==========

``pip-review`` checks PyPI and reports available updates.  It uses the list of
currently installed packages to check for updates, it does not use any
``requirements.txt``.

Example, report-only:

.. code:: console

    $ pip-review
    requests==0.13.4 available (you have 0.13.2)
    redis==2.4.13 available (you have 2.4.9)
    rq==0.3.2 available (you have 0.3.0)

Example, actually install everything:

.. code:: console

    $ pip-review --auto
    ... <pip install output>

Example, run interactively, ask to upgrade for each package:

.. code:: console

    $ pip-review --interactive
    requests==0.14.0 available (you have 0.13.2)
    Upgrade now? [Y]es, [N]o, [A]ll, [Q]uit y
    ...
    redis==2.6.2 available (you have 2.4.9)
    Upgrade now? [Y]es, [N]o, [A]ll, [Q]uit n
    rq==0.3.2 available (you have 0.3.0)
    Upgrade now? [Y]es, [N]o, [A]ll, [Q]uit y
    ...

Up until version 0.3.7, ``pip-review`` would show and install any available
update including pre-release versions. As of version 0.4, it will only show and
install release versions by default. To restore the original behaviour, use the
``--pre`` flag.

Since version 0.5, you can also invoke pip-review as ``python -m pip_review``. **This is the only way to invoke pip-review that enables it to update itself.**


Installation
============

To install, simply use pip:

.. code:: console

    $ pip install pip-review

Decide for yourself whether you want to install the tool system-wide, or
inside a virtual env.  Both are supported.


Testing
=======

To test with your active Python version:

.. code:: console

    $ ./run-tests.sh

To test under all (supported) Python versions:

.. code:: console

    $ tox

The tests run quite slow, since they actually interact with PyPI, which
involves downloading packages, etc.  So please be patient.


Origins
=======

``pip-review`` was originally part of pip-tools_ but 
has been discontinued_ as such. See `Pin Your Packages`_ by Vincent
Driessen for the original introduction. Since there are still use cases, the
tool now lives on as a separate package.


.. _pip-tools: https://github.com/nvie/pip-tools/
.. _discontinued: https://github.com/nvie/pip-tools/issues/185
.. _Pin Your Packages: http://nvie.com/posts/pin-your-packages/
.. _cram: https://bitheap.org/cram/
