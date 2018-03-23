Vendored libs policy
====================

* Vendored libraries **MUST** not be modified except as required to
  successfully vendor them.

* Vendored libraries **MUST** be released copies of libraries available on
  PyPI.

* The versions of libraries vendored in pip-tools **MUST** be reflected
  in the section below.

* Vendored libraries **MUST** function without any build steps such as 2to3 or
  compilation of C code, practically this limits to single source 2.x/3.x and
  pure Python.

* Any modifications made to libraries **MUST** be noted in the section below.


Versions and modifications:
===========================

* ``pip`` == 9.0.3

  Modifications:
    - None.

  Reason: ``pip`` 10.x internal changes break the dependency resolution code for ``pip-compile``.
    Note that ``pip-sync`` still uses the user-installed ``pip`` to perform the install/uninstall operations.