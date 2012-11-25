Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install argparse >/dev/null 2>&1
  $ export PYTHONPATH=$PYTHONPATH:$TESTDIR/..
  $ alias pip-compile="$TESTDIR/../bin/pip-compile"

Let's create a couple of simple requirements.in files:

  $ echo "nose" > dev-requirements.in
  $ echo "raven==1.9.3" > requirements.in

Compile with --dry-run:

  $ pip-compile --dry-run --verbose
  ===> Collecting source requirements
  nose (from dev-requirements.in:1)
  raven==1.9.3 (from requirements.in:1)
  
  ===> Normalizing source requirements
  nose (from dev-requirements.in:1)
  raven==1.9.3 (from requirements.in:1)
  
  ===> Resolving full tree
  - Finding best package matching ['nose']
    Found best match: 1.2.1 (from PyPI)
  - Getting dependencies for nose-1.2.1
    Found: [] (from dependency cache)
  - Finding best package matching ['raven==1.9.3']
    Found best match: 1.9.3 (from dependency cache)
  - Getting dependencies for raven-1.9.3
    Found: ['simplejson>=2.3.0,<2.5.0'] (from dependency cache)
  After round #1:
    - nose (from dev-requirements.in:1)
    - raven==1.9.3 (from requirements.in:1)
    - simplejson>=2.3.0,<2.5.0 (from requirements.in:1 ~> raven==1.9.3)
  - Finding best package matching ['nose']
    Found best match: 1.2.1 (from link cache)
  - Finding best package matching ['simplejson>=2.3.0,<2.5.0']
    Found best match: 2.4.0 (from PyPI)
  - Getting dependencies for simplejson-2.4.0
    Found: [] (from dependency cache)
  - Finding best package matching ['nose']
    Found best match: 1.2.1 (from link cache)
  - Finding best package matching ['simplejson>=2.3.0,<2.5.0']
    Found best match: 2.4.0 (from link cache)
  
  ===> Pinned spec set resolved
  - nose==1.2.1
  - raven==1.9.3
  - simplejson==2.4.0
  Dry-run, so nothing updated.

Let's create a simple requirements.in file:

  $ rm dev-requirements.in
  $ echo "raven==1.9.3" > requirements.in
  $ echo "simplejson==2.3.3" >> requirements.in

Compile with --dry-run:

  $ pip-compile --dry-run --verbose
  ===> Collecting source requirements
  raven==1.9.3 (from requirements.in:1)
  simplejson==2.3.3 (from requirements.in:2)
  
  ===> Normalizing source requirements
  raven==1.9.3 (from requirements.in:1)
  simplejson==2.3.3 (from requirements.in:2)
  
  ===> Resolving full tree
  - Finding best package matching ['raven==1.9.3']
    Found best match: 1.9.3 (from dependency cache)
  - Getting dependencies for raven-1.9.3
    Found: ['simplejson>=2.3.0,<2.5.0'] (from dependency cache)
  - Finding best package matching ['simplejson==2.3.3']
    Found best match: 2.3.3 (from dependency cache)
  - Getting dependencies for simplejson-2.3.3
    Found: [] (from dependency cache)
  After round #1:
    - raven==1.9.3 (from requirements.in:1)
    - simplejson==2.3.3 (from requirements.in:2)
    - simplejson>=2.3.0,<2.5.0 (from requirements.in:1 ~> raven==1.9.3)
  
  ===> Pinned spec set resolved
  - raven==1.9.3
  - simplejson==2.3.3
  Dry-run, so nothing updated.

Let's create a simple requirements.in file:

  $ echo "sentry==5.0.13" > requirements.in

Compile with --dry-run:

  $ pip-compile --dry-run --verbose
  ===> Collecting source requirements
  sentry==5.0.13 (from requirements.in:1)
  
  ===> Normalizing source requirements
  sentry==5.0.13 (from requirements.in:1)
  
  ===> Resolving full tree
  - Finding best package matching ['sentry==5.0.13']
    Found best match: 5.0.13 (from dependency cache)
  - Getting dependencies for sentry-5.0.13
    Found: ['cssutils>=0.9.9', 'BeautifulSoup>=3.2.1', 'django-celery>=2.5.5', 'celery>=2.5.3', 'django-crispy-forms>=1.1.4', 'Django>=1.4.1,<=1.5', 'django-indexer>=0.3.0', 'django-paging>=0.2.4', 'django-picklefield>=0.2.0', 'django-templatetag-sugar>=0.1.0', 'gunicorn>=0.14.6', 'logan>=0.5.0', 'pynliner>=0.4.0', 'python-dateutil>=1.5.0,<2.0.0', 'raven>=2.0.6', 'simplejson>=2.1.6', 'South>=0.7.6', 'httpagentparser>=1.0.5', 'django-social-auth>=0.7.1,<1.0', 'django-social-auth-trello>=1.0.2'] (from dependency cache)
  After round #1:
    - BeautifulSoup>=3.2.1 (from requirements.in:1 ~> sentry==5.0.13)
    - Django>=1.4.1,<=1.5 (from requirements.in:1 ~> sentry==5.0.13)
    - South>=0.7.6 (from requirements.in:1 ~> sentry==5.0.13)
    - celery>=2.5.3 (from requirements.in:1 ~> sentry==5.0.13)
    - cssutils>=0.9.9 (from requirements.in:1 ~> sentry==5.0.13)
    - django-celery>=2.5.5 (from requirements.in:1 ~> sentry==5.0.13)
    - django-crispy-forms>=1.1.4 (from requirements.in:1 ~> sentry==5.0.13)
    - django-indexer>=0.3.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-paging>=0.2.4 (from requirements.in:1 ~> sentry==5.0.13)
    - django-picklefield>=0.2.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-social-auth-trello>=1.0.2 (from requirements.in:1 ~> sentry==5.0.13)
    - django-social-auth>=0.7.1,<1.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-templatetag-sugar>=0.1.0 (from requirements.in:1 ~> sentry==5.0.13)
    - gunicorn>=0.14.6 (from requirements.in:1 ~> sentry==5.0.13)
    - httpagentparser>=1.0.5 (from requirements.in:1 ~> sentry==5.0.13)
    - logan>=0.5.0 (from requirements.in:1 ~> sentry==5.0.13)
    - pynliner>=0.4.0 (from requirements.in:1 ~> sentry==5.0.13)
    - python-dateutil>=1.5.0,<2.0.0 (from requirements.in:1 ~> sentry==5.0.13)
    - raven>=2.0.6 (from requirements.in:1 ~> sentry==5.0.13)
    - sentry==5.0.13 (from requirements.in:1)
    - simplejson>=2.1.6 (from requirements.in:1 ~> sentry==5.0.13)
  - Finding best package matching ['BeautifulSoup>=3.2.1']
    Found best match: 3.2.1 (from PyPI)
  - Getting dependencies for BeautifulSoup-3.2.1
    Found: [] (from dependency cache)
  - Finding best package matching ['celery>=2.5.3']
    Found best match: 3.0.12 (from PyPI)
  - Getting dependencies for celery-3.0.12
    Found: ['billiard>=2.7.3.18', 'python-dateutil>=1.5,<2.0', 'kombu>=2.4.8,<3.0'] (from dependency cache)
  - Finding best package matching ['cssutils>=0.9.9']
    Found best match: 0.9.10b1 (from PyPI)
  - Getting dependencies for cssutils-0.9.10b1
    Found: [] (from dependency cache)
  - Finding best package matching ['Django>=1.4.1,<=1.5']
    Found best match: 1.4.2 (from PyPI)
  - Getting dependencies for Django-1.4.2
    Found: [] (from dependency cache)
  - Finding best package matching ['django-celery>=2.5.5']
    Found best match: 3.0.11 (from PyPI)
  - Getting dependencies for django-celery-3.0.11
    Found: ['pytz', 'celery>=3.0.11'] (from dependency cache)
  - Finding best package matching ['django-crispy-forms>=1.1.4']
    Found best match: 1.2.0 (from PyPI)
  - Getting dependencies for django-crispy-forms-1.2.0
    Found: [] (from dependency cache)
  - Finding best package matching ['django-indexer>=0.3.0']
    Found best match: 0.3.0 (from PyPI)
  - Getting dependencies for django-indexer-0.3.0
    Found: [] (from dependency cache)
  - Finding best package matching ['django-paging>=0.2.4']
    Found best match: 0.2.4 (from PyPI)
  - Getting dependencies for django-paging-0.2.4
    Found: ['django-templatetag-sugar>=0.1'] (from dependency cache)
  - Finding best package matching ['django-picklefield>=0.2.0']
    Found best match: 0.2.1 (from PyPI)
  - Getting dependencies for django-picklefield-0.2.1
    Found: [] (from dependency cache)
  - Finding best package matching ['django-social-auth>=0.7.1,<1.0']
    Found best match: 0.7.10 (from PyPI)
  - Getting dependencies for django-social-auth-0.7.10
    Found: ['django>=1.2.5', 'oauth2>=1.5.167', 'python_openid>=2.2'] (from dependency cache)
  - Finding best package matching ['django-social-auth-trello>=1.0.2']
    Found best match: 1.0.2 (from PyPI)
  - Getting dependencies for django-social-auth-trello-1.0.2
    Found: ['django-social-auth'] (from dependency cache)
  - Finding best package matching ['django-templatetag-sugar>=0.1.0']
    Found best match: 0.1 (from PyPI)
  - Getting dependencies for django-templatetag-sugar-0.1
    Found: [] (from dependency cache)
  - Finding best package matching ['gunicorn>=0.14.6']
    Found best match: 0.16.1 (from PyPI)
  - Getting dependencies for gunicorn-0.16.1
    Found: [] (from dependency cache)
  - Finding best package matching ['httpagentparser>=1.0.5']
    Found best match: 1.2.1 (from PyPI)
  - Getting dependencies for httpagentparser-1.2.1
    Found: [] (from dependency cache)
  - Finding best package matching ['logan>=0.5.0']
    Found best match: 0.5.1 (from PyPI)
  - Getting dependencies for logan-0.5.1
    Found: [] (from dependency cache)
  - Finding best package matching ['pynliner>=0.4.0']
    Found best match: 0.4.0 (from PyPI)
  - Getting dependencies for pynliner-0.4.0
    Found: [] (from dependency cache)
  - Finding best package matching ['python-dateutil>=1.5.0,<2.0.0']
    Found best match: 1.5 (from PyPI)
  - Getting dependencies for python-dateutil-1.5
    Found: [] (from dependency cache)
  - Finding best package matching ['raven>=2.0.6']
    Found best match: 2.0.10 (from PyPI)
  - Getting dependencies for raven-2.0.10
    Found: [] (from dependency cache)
  - Finding best package matching ['simplejson>=2.1.6']
    Found best match: 2.6.2 (from PyPI)
  - Getting dependencies for simplejson-2.6.2
    Found: [] (from dependency cache)
  - Finding best package matching ['South>=0.7.6']
    Found best match: 0.7.6 (from PyPI)
  - Getting dependencies for South-0.7.6
    Found: [] (from dependency cache)
  After round #2:
    - BeautifulSoup>=3.2.1 (from requirements.in:1 ~> sentry==5.0.13)
    - Django>=1.4.1,<=1.5 (from requirements.in:1 ~> sentry==5.0.13)
    - South>=0.7.6 (from requirements.in:1 ~> sentry==5.0.13)
    - billiard>=2.7.3.18 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12)
    - celery>=2.5.3 (from requirements.in:1 ~> sentry==5.0.13)
    - celery>=3.0.11 (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11)
    - cssutils>=0.9.9 (from requirements.in:1 ~> sentry==5.0.13)
    - django-celery>=2.5.5 (from requirements.in:1 ~> sentry==5.0.13)
    - django-crispy-forms>=1.1.4 (from requirements.in:1 ~> sentry==5.0.13)
    - django-indexer>=0.3.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-paging>=0.2.4 (from requirements.in:1 ~> sentry==5.0.13)
    - django-picklefield>=0.2.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-social-auth (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth-trello==1.0.2)
    - django-social-auth-trello>=1.0.2 (from requirements.in:1 ~> sentry==5.0.13)
    - django-social-auth>=0.7.1,<1.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-templatetag-sugar>=0.1 (from requirements.in:1 ~> sentry==5.0.13 ~> django-paging==0.2.4)
    - django-templatetag-sugar>=0.1.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django>=1.2.5 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10)
    - gunicorn>=0.14.6 (from requirements.in:1 ~> sentry==5.0.13)
    - httpagentparser>=1.0.5 (from requirements.in:1 ~> sentry==5.0.13)
    - kombu>=2.4.8,<3.0 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12)
    - logan>=0.5.0 (from requirements.in:1 ~> sentry==5.0.13)
    - oauth2>=1.5.167 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10)
    - pynliner>=0.4.0 (from requirements.in:1 ~> sentry==5.0.13)
    - python-dateutil>=1.5,<2.0 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12)
    - python-dateutil>=1.5.0,<2.0.0 (from requirements.in:1 ~> sentry==5.0.13)
    - python-openid>=2.2 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10)
    - pytz (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11)
    - raven>=2.0.6 (from requirements.in:1 ~> sentry==5.0.13)
    - sentry==5.0.13 (from requirements.in:1)
    - simplejson>=2.1.6 (from requirements.in:1 ~> sentry==5.0.13)
  - Finding best package matching ['BeautifulSoup>=3.2.1']
    Found best match: 3.2.1 (from link cache)
  - Finding best package matching ['billiard>=2.7.3.18']
    Found best match: 2.7.3.18 (from PyPI)
  - Getting dependencies for billiard-2.7.3.18
    Found: [] (from dependency cache)
  - Finding best package matching ['celery>=3.0.11']
    Found best match: 3.0.12 (from PyPI)
  - Finding best package matching ['cssutils>=0.9.9']
    Found best match: 0.9.10b1 (from link cache)
  - Finding best package matching ['Django>=1.4.1,<=1.5']
    Found best match: 1.4.2 (from link cache)
  - Finding best package matching ['django>=1.2.5']
    Found best match: 1.4.2 (from PyPI)
  - Getting dependencies for django-1.4.2
    Found: [] (from dependency cache)
  - Finding best package matching ['django-celery>=2.5.5']
    Found best match: 3.0.11 (from link cache)
  - Finding best package matching ['django-crispy-forms>=1.1.4']
    Found best match: 1.2.0 (from link cache)
  - Finding best package matching ['django-indexer>=0.3.0']
    Found best match: 0.3.0 (from link cache)
  - Finding best package matching ['django-paging>=0.2.4']
    Found best match: 0.2.4 (from link cache)
  - Finding best package matching ['django-picklefield>=0.2.0']
    Found best match: 0.2.1 (from link cache)
  - Finding best package matching ['django-social-auth>=0.7.1,<1.0']
    Found best match: 0.7.10 (from link cache)
  - Finding best package matching ['django-social-auth-trello>=1.0.2']
    Found best match: 1.0.2 (from link cache)
  - Finding best package matching ['django-templatetag-sugar>=0.1.0']
    Found best match: 0.1 (from link cache)
  - Finding best package matching ['gunicorn>=0.14.6']
    Found best match: 0.16.1 (from link cache)
  - Finding best package matching ['httpagentparser>=1.0.5']
    Found best match: 1.2.1 (from link cache)
  - Finding best package matching ['kombu>=2.4.8,<3.0']
    Found best match: 2.4.10 (from PyPI)
  - Getting dependencies for kombu-2.4.10
    Found: ['anyjson>=0.3.3', 'amqplib>=1.0.2'] (from dependency cache)
  - Finding best package matching ['logan>=0.5.0']
    Found best match: 0.5.1 (from link cache)
  - Finding best package matching ['oauth2>=1.5.167']
    Found best match: 1.5.211 (from PyPI)
  - Getting dependencies for oauth2-1.5.211
    Found: ['httplib2'] (from dependency cache)
  - Finding best package matching ['pynliner>=0.4.0']
    Found best match: 0.4.0 (from link cache)
  - Finding best package matching ['python-dateutil>=1.5.0,<2.0']
    Found best match: 1.5 (from PyPI)
  - Finding best package matching ['python-openid>=2.2']
    Found best match: 2.2.5 (from PyPI)
  - Getting dependencies for python-openid-2.2.5
    Found: [] (from dependency cache)
  - Finding best package matching ['pytz']
    Found best match: 2012h (from PyPI)
  - Getting dependencies for pytz-2012h
    Found: [] (from dependency cache)
  - Finding best package matching ['raven>=2.0.6']
    Found best match: 2.0.10 (from link cache)
  - Finding best package matching ['simplejson>=2.1.6']
    Found best match: 2.6.2 (from link cache)
  - Finding best package matching ['South>=0.7.6']
    Found best match: 0.7.6 (from link cache)
  After round #3:
    - BeautifulSoup>=3.2.1 (from requirements.in:1 ~> sentry==5.0.13)
    - Django>=1.4.1,<=1.5 (from requirements.in:1 ~> sentry==5.0.13)
    - South>=0.7.6 (from requirements.in:1 ~> sentry==5.0.13)
    - amqplib>=1.0.2 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12 ~> kombu==2.4.10)
    - anyjson>=0.3.3 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12 ~> kombu==2.4.10)
    - billiard>=2.7.3.18 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12)
    - billiard>=2.7.3.18 (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11 ~> celery==3.0.12)
    - celery>=2.5.3 (from requirements.in:1 ~> sentry==5.0.13)
    - celery>=3.0.11 (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11)
    - cssutils>=0.9.9 (from requirements.in:1 ~> sentry==5.0.13)
    - django-celery>=2.5.5 (from requirements.in:1 ~> sentry==5.0.13)
    - django-crispy-forms>=1.1.4 (from requirements.in:1 ~> sentry==5.0.13)
    - django-indexer>=0.3.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-paging>=0.2.4 (from requirements.in:1 ~> sentry==5.0.13)
    - django-picklefield>=0.2.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-social-auth (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth-trello==1.0.2)
    - django-social-auth-trello>=1.0.2 (from requirements.in:1 ~> sentry==5.0.13)
    - django-social-auth>=0.7.1,<1.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-templatetag-sugar>=0.1 (from requirements.in:1 ~> sentry==5.0.13 ~> django-paging==0.2.4)
    - django-templatetag-sugar>=0.1.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django>=1.2.5 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10)
    - gunicorn>=0.14.6 (from requirements.in:1 ~> sentry==5.0.13)
    - httpagentparser>=1.0.5 (from requirements.in:1 ~> sentry==5.0.13)
    - httplib2 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10 ~> oauth2==1.5.211)
    - kombu>=2.4.8,<3.0 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12)
    - kombu>=2.4.8,<3.0 (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11 ~> celery==3.0.12)
    - logan>=0.5.0 (from requirements.in:1 ~> sentry==5.0.13)
    - oauth2>=1.5.167 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10)
    - pynliner>=0.4.0 (from requirements.in:1 ~> sentry==5.0.13)
    - python-dateutil>=1.5,<2.0 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12)
    - python-dateutil>=1.5,<2.0 (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11 ~> celery==3.0.12)
    - python-dateutil>=1.5.0,<2.0.0 (from requirements.in:1 ~> sentry==5.0.13)
    - python-openid>=2.2 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10)
    - pytz (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11)
    - raven>=2.0.6 (from requirements.in:1 ~> sentry==5.0.13)
    - sentry==5.0.13 (from requirements.in:1)
    - simplejson>=2.1.6 (from requirements.in:1 ~> sentry==5.0.13)
  - Finding best package matching ['amqplib>=1.0.2']
    Found best match: 1.0.2 (from PyPI)
  - Getting dependencies for amqplib-1.0.2
    Found: [] (from dependency cache)
  - Finding best package matching ['anyjson>=0.3.3']
    Found best match: 0.3.3 (from PyPI)
  - Getting dependencies for anyjson-0.3.3
    Found: [] (from dependency cache)
  - Finding best package matching ['BeautifulSoup>=3.2.1']
    Found best match: 3.2.1 (from link cache)
  - Finding best package matching ['billiard>=2.7.3.18']
    Found best match: 2.7.3.18 (from link cache)
  - Finding best package matching ['celery>=3.0.11']
    Found best match: 3.0.12 (from link cache)
  - Finding best package matching ['cssutils>=0.9.9']
    Found best match: 0.9.10b1 (from link cache)
  - Finding best package matching ['Django>=1.4.1,<=1.5']
    Found best match: 1.4.2 (from link cache)
  - Finding best package matching ['django>=1.2.5']
    Found best match: 1.4.2 (from link cache)
  - Finding best package matching ['django-celery>=2.5.5']
    Found best match: 3.0.11 (from link cache)
  - Finding best package matching ['django-crispy-forms>=1.1.4']
    Found best match: 1.2.0 (from link cache)
  - Finding best package matching ['django-indexer>=0.3.0']
    Found best match: 0.3.0 (from link cache)
  - Finding best package matching ['django-paging>=0.2.4']
    Found best match: 0.2.4 (from link cache)
  - Finding best package matching ['django-picklefield>=0.2.0']
    Found best match: 0.2.1 (from link cache)
  - Finding best package matching ['django-social-auth>=0.7.1,<1.0']
    Found best match: 0.7.10 (from link cache)
  - Finding best package matching ['django-social-auth-trello>=1.0.2']
    Found best match: 1.0.2 (from link cache)
  - Finding best package matching ['django-templatetag-sugar>=0.1.0']
    Found best match: 0.1 (from link cache)
  - Finding best package matching ['gunicorn>=0.14.6']
    Found best match: 0.16.1 (from link cache)
  - Finding best package matching ['httpagentparser>=1.0.5']
    Found best match: 1.2.1 (from link cache)
  - Finding best package matching ['httplib2']
    Found best match: 0.7.7 (from PyPI)
  - Getting dependencies for httplib2-0.7.7
    Found: [] (from dependency cache)
  - Finding best package matching ['kombu>=2.4.8,<3.0']
    Found best match: 2.4.10 (from link cache)
  - Finding best package matching ['logan>=0.5.0']
    Found best match: 0.5.1 (from link cache)
  - Finding best package matching ['oauth2>=1.5.167']
    Found best match: 1.5.211 (from link cache)
  - Finding best package matching ['pynliner>=0.4.0']
    Found best match: 0.4.0 (from link cache)
  - Finding best package matching ['python-dateutil>=1.5.0,<2.0']
    Found best match: 1.5 (from link cache)
  - Finding best package matching ['python-openid>=2.2']
    Found best match: 2.2.5 (from link cache)
  - Finding best package matching ['pytz']
    Found best match: 2012h (from link cache)
  - Finding best package matching ['raven>=2.0.6']
    Found best match: 2.0.10 (from link cache)
  - Finding best package matching ['simplejson>=2.1.6']
    Found best match: 2.6.2 (from link cache)
  - Finding best package matching ['South>=0.7.6']
    Found best match: 0.7.6 (from link cache)
  After round #4:
    - BeautifulSoup>=3.2.1 (from requirements.in:1 ~> sentry==5.0.13)
    - Django>=1.4.1,<=1.5 (from requirements.in:1 ~> sentry==5.0.13)
    - South>=0.7.6 (from requirements.in:1 ~> sentry==5.0.13)
    - amqplib>=1.0.2 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12 and requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11 ~> celery==3.0.12 ~> kombu==2.4.10)
    - amqplib>=1.0.2 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12 ~> kombu==2.4.10)
    - anyjson>=0.3.3 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12 and requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11 ~> celery==3.0.12 ~> kombu==2.4.10)
    - anyjson>=0.3.3 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12 ~> kombu==2.4.10)
    - billiard>=2.7.3.18 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12)
    - billiard>=2.7.3.18 (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11 ~> celery==3.0.12)
    - celery>=2.5.3 (from requirements.in:1 ~> sentry==5.0.13)
    - celery>=3.0.11 (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11)
    - cssutils>=0.9.9 (from requirements.in:1 ~> sentry==5.0.13)
    - django-celery>=2.5.5 (from requirements.in:1 ~> sentry==5.0.13)
    - django-crispy-forms>=1.1.4 (from requirements.in:1 ~> sentry==5.0.13)
    - django-indexer>=0.3.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-paging>=0.2.4 (from requirements.in:1 ~> sentry==5.0.13)
    - django-picklefield>=0.2.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-social-auth (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth-trello==1.0.2)
    - django-social-auth-trello>=1.0.2 (from requirements.in:1 ~> sentry==5.0.13)
    - django-social-auth>=0.7.1,<1.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django-templatetag-sugar>=0.1 (from requirements.in:1 ~> sentry==5.0.13 ~> django-paging==0.2.4)
    - django-templatetag-sugar>=0.1.0 (from requirements.in:1 ~> sentry==5.0.13)
    - django>=1.2.5 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10)
    - gunicorn>=0.14.6 (from requirements.in:1 ~> sentry==5.0.13)
    - httpagentparser>=1.0.5 (from requirements.in:1 ~> sentry==5.0.13)
    - httplib2 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10 ~> oauth2==1.5.211)
    - kombu>=2.4.8,<3.0 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12)
    - kombu>=2.4.8,<3.0 (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11 ~> celery==3.0.12)
    - logan>=0.5.0 (from requirements.in:1 ~> sentry==5.0.13)
    - oauth2>=1.5.167 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10)
    - pynliner>=0.4.0 (from requirements.in:1 ~> sentry==5.0.13)
    - python-dateutil>=1.5,<2.0 (from requirements.in:1 ~> sentry==5.0.13 ~> celery==3.0.12)
    - python-dateutil>=1.5,<2.0 (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11 ~> celery==3.0.12)
    - python-dateutil>=1.5.0,<2.0.0 (from requirements.in:1 ~> sentry==5.0.13)
    - python-openid>=2.2 (from requirements.in:1 ~> sentry==5.0.13 ~> django-social-auth==0.7.10)
    - pytz (from requirements.in:1 ~> sentry==5.0.13 ~> django-celery==3.0.11)
    - raven>=2.0.6 (from requirements.in:1 ~> sentry==5.0.13)
    - sentry==5.0.13 (from requirements.in:1)
    - simplejson>=2.1.6 (from requirements.in:1 ~> sentry==5.0.13)
  - Finding best package matching ['amqplib>=1.0.2']
    Found best match: 1.0.2 (from link cache)
  - Finding best package matching ['anyjson>=0.3.3']
    Found best match: 0.3.3 (from link cache)
  - Finding best package matching ['BeautifulSoup>=3.2.1']
    Found best match: 3.2.1 (from link cache)
  - Finding best package matching ['billiard>=2.7.3.18']
    Found best match: 2.7.3.18 (from link cache)
  - Finding best package matching ['celery>=3.0.11']
    Found best match: 3.0.12 (from link cache)
  - Finding best package matching ['cssutils>=0.9.9']
    Found best match: 0.9.10b1 (from link cache)
  - Finding best package matching ['Django>=1.4.1,<=1.5']
    Found best match: 1.4.2 (from link cache)
  - Finding best package matching ['django>=1.2.5']
    Found best match: 1.4.2 (from link cache)
  - Finding best package matching ['django-celery>=2.5.5']
    Found best match: 3.0.11 (from link cache)
  - Finding best package matching ['django-crispy-forms>=1.1.4']
    Found best match: 1.2.0 (from link cache)
  - Finding best package matching ['django-indexer>=0.3.0']
    Found best match: 0.3.0 (from link cache)
  - Finding best package matching ['django-paging>=0.2.4']
    Found best match: 0.2.4 (from link cache)
  - Finding best package matching ['django-picklefield>=0.2.0']
    Found best match: 0.2.1 (from link cache)
  - Finding best package matching ['django-social-auth>=0.7.1,<1.0']
    Found best match: 0.7.10 (from link cache)
  - Finding best package matching ['django-social-auth-trello>=1.0.2']
    Found best match: 1.0.2 (from link cache)
  - Finding best package matching ['django-templatetag-sugar>=0.1.0']
    Found best match: 0.1 (from link cache)
  - Finding best package matching ['gunicorn>=0.14.6']
    Found best match: 0.16.1 (from link cache)
  - Finding best package matching ['httpagentparser>=1.0.5']
    Found best match: 1.2.1 (from link cache)
  - Finding best package matching ['httplib2']
    Found best match: 0.7.7 (from link cache)
  - Finding best package matching ['kombu>=2.4.8,<3.0']
    Found best match: 2.4.10 (from link cache)
  - Finding best package matching ['logan>=0.5.0']
    Found best match: 0.5.1 (from link cache)
  - Finding best package matching ['oauth2>=1.5.167']
    Found best match: 1.5.211 (from link cache)
  - Finding best package matching ['pynliner>=0.4.0']
    Found best match: 0.4.0 (from link cache)
  - Finding best package matching ['python-dateutil>=1.5.0,<2.0']
    Found best match: 1.5 (from link cache)
  - Finding best package matching ['python-openid>=2.2']
    Found best match: 2.2.5 (from link cache)
  - Finding best package matching ['pytz']
    Found best match: 2012h (from link cache)
  - Finding best package matching ['raven>=2.0.6']
    Found best match: 2.0.10 (from link cache)
  - Finding best package matching ['simplejson>=2.1.6']
    Found best match: 2.6.2 (from link cache)
  - Finding best package matching ['South>=0.7.6']
    Found best match: 0.7.6 (from link cache)
  - Finding best package matching ['amqplib>=1.0.2']
    Found best match: 1.0.2 (from link cache)
  - Finding best package matching ['anyjson>=0.3.3']
    Found best match: 0.3.3 (from link cache)
  - Finding best package matching ['BeautifulSoup>=3.2.1']
    Found best match: 3.2.1 (from link cache)
  - Finding best package matching ['billiard>=2.7.3.18']
    Found best match: 2.7.3.18 (from link cache)
  - Finding best package matching ['celery>=3.0.11']
    Found best match: 3.0.12 (from link cache)
  - Finding best package matching ['cssutils>=0.9.9']
    Found best match: 0.9.10b1 (from link cache)
  - Finding best package matching ['Django>=1.4.1,<=1.5']
    Found best match: 1.4.2 (from link cache)
  - Finding best package matching ['django>=1.2.5']
    Found best match: 1.4.2 (from link cache)
  - Finding best package matching ['django-celery>=2.5.5']
    Found best match: 3.0.11 (from link cache)
  - Finding best package matching ['django-crispy-forms>=1.1.4']
    Found best match: 1.2.0 (from link cache)
  - Finding best package matching ['django-indexer>=0.3.0']
    Found best match: 0.3.0 (from link cache)
  - Finding best package matching ['django-paging>=0.2.4']
    Found best match: 0.2.4 (from link cache)
  - Finding best package matching ['django-picklefield>=0.2.0']
    Found best match: 0.2.1 (from link cache)
  - Finding best package matching ['django-social-auth>=0.7.1,<1.0']
    Found best match: 0.7.10 (from link cache)
  - Finding best package matching ['django-social-auth-trello>=1.0.2']
    Found best match: 1.0.2 (from link cache)
  - Finding best package matching ['django-templatetag-sugar>=0.1.0']
    Found best match: 0.1 (from link cache)
  - Finding best package matching ['gunicorn>=0.14.6']
    Found best match: 0.16.1 (from link cache)
  - Finding best package matching ['httpagentparser>=1.0.5']
    Found best match: 1.2.1 (from link cache)
  - Finding best package matching ['httplib2']
    Found best match: 0.7.7 (from link cache)
  - Finding best package matching ['kombu>=2.4.8,<3.0']
    Found best match: 2.4.10 (from link cache)
  - Finding best package matching ['logan>=0.5.0']
    Found best match: 0.5.1 (from link cache)
  - Finding best package matching ['oauth2>=1.5.167']
    Found best match: 1.5.211 (from link cache)
  - Finding best package matching ['pynliner>=0.4.0']
    Found best match: 0.4.0 (from link cache)
  - Finding best package matching ['python-dateutil>=1.5.0,<2.0']
    Found best match: 1.5 (from link cache)
  - Finding best package matching ['python-openid>=2.2']
    Found best match: 2.2.5 (from link cache)
  - Finding best package matching ['pytz']
    Found best match: 2012h (from link cache)
  - Finding best package matching ['raven>=2.0.6']
    Found best match: 2.0.10 (from link cache)
  - Finding best package matching ['simplejson>=2.1.6']
    Found best match: 2.6.2 (from link cache)
  - Finding best package matching ['South>=0.7.6']
    Found best match: 0.7.6 (from link cache)
  
  ===> Pinned spec set resolved
  - amqplib==1.0.2
  - anyjson==0.3.3
  - BeautifulSoup==3.2.1
  - billiard==2.7.3.18
  - celery==3.0.12
  - cssutils==0.9.10b1
  - Django==1.4.2
  - django==1.4.2
  - django-celery==3.0.11
  - django-crispy-forms==1.2.0
  - django-indexer==0.3.0
  - django-paging==0.2.4
  - django-picklefield==0.2.1
  - django-social-auth==0.7.10
  - django-social-auth-trello==1.0.2
  - django-templatetag-sugar==0.1
  - gunicorn==0.16.1
  - httpagentparser==1.2.1
  - httplib2==0.7.7
  - kombu==2.4.10
  - logan==0.5.1
  - oauth2==1.5.211
  - pynliner==0.4.0
  - python-dateutil==1.5
  - python-openid==2.2.5
  - pytz==2012h
  - raven==2.0.10
  - sentry==5.0.13
  - simplejson==2.6.2
  - South==0.7.6
  Dry-run, so nothing updated.
