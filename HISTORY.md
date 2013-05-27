History
=======

0.3.2 (2013-05-27)
------------------
   - Improve logging semantics (John Mark Schofield)
   - Remove ``verlib`` dependency (it's officially unmaintained)
     (Vladimir Rudnyh)
   - Adds package name guessing using PyPI's ``/simple`` API endpoint
     (Vladimir Rudnyh)

0.3.1 (2013-03-20)
------------------
   - Add ``--local`` flag, to only review packages from the virtual env,
   	 ignoring globally installed packages

0.3 (2013-03-20)
----------------
   - Compares versions, so version numbers reported are always higher than the
   	 current versions (assumes PEP 386 compliance)
   - Detects more filename patterns for requirements files

0.2.1 (2012-10-26)
------------------
   - Python 2.6 support

0.2 (2012-09-26)
----------------
   - Fix --editables support

0.1 (2012-09-26)
----------------
   - Initial release
