Create a new playground first:

  $ virtualenv --python="$(which python)" FOO >/dev/null
  $ PATH=FOO/bin:$PATH
  $ pip install argparse >/dev/null 2>&1
  $ alias pip-compile="$TESTDIR/../bin/pip-compile"

Let's create a simple requirements.in file:

  $ cat requirements.in
  raven==1.9.3

Compile with --dry-run:

  $ pip-compile --dry-run --verbose
  ===> Parsing source requirements
  requirements.in: raven==1.9.3
  dev-requirements.in: nose
  ===> Unfolding dependency tree
  raven==1.9.3
    simplejson>=2.3.0,<2.5.0
  nose
  ===> Compiling pinned versions
  raven==1.9.3
    simplejson==2.4.0
  nose==1.2.1
  ===> Writing out requirements.txt
  raven==1.9.3
  simplejson==2.4.0
  ===> Writing out dev-requirements.txt
  nose==1.2.1

Let's create a simple requirements.in file:

  $ cat requirements.in
  raven==1.9.3
  simplejson==2.3.3

Compile with --dry-run:

  $ pip-compile --dry-run --verbose
  ===> Parsing source requirements
  requirements.in: raven==1.9.3
  requirements.in: simplejson==2.3.3
  dev-requirements.in: nose
  ===> Unfolding dependency tree
  raven==1.9.3
    simplejson>=2.3.0,<2.5.0
  simplejson==2.3.3
  nose
  ===> Compiling pinned versions
  raven==1.9.3
  simplejson==2.3.3
  nose==1.2.1
  ===> Writing out requirements.txt
  raven==1.9.3
  simplejson==2.3.3
  ===> Writing out dev-requirements.txt
  nose==1.2.1

Let's create a simple requirements.in file:

  $ cat requirements.in
  sentry==5.0.13

Compile with --dry-run:

  $ pip-compile --dry-run --verbose
  ===> Parsing source requirements
  requirements.in: sentry==5.0.13
  ===> Unfolding dependency tree
  sentry==5.0.13
    cssutils>=0.9.9
    BeautifulSoup>=3.2.1
    django-celery>=2.5.5
    celery>=2.5.3
      billiard>=2.7.3.17
      kombu>=2.4.7,<3.0
        anyjson>=0.3.3
        amqplib>=1.0.2
    django-crispy-forms>=1.1.4
    Django>=1.4.1,<=1.5
    django-indexer>=0.3.0
    django-paging>=0.2.4
    django-picklefield>=0.2.0
    django-templatetag-sugar>=0.1.0
    gunicorn>=0.14.6
    logan>=0.5.0
    pynliner>=0.4.0
    python-dateutil>=1.5.0,<2.0.0
    raven>=2.0.6
    South>=0.7.6
    httpagentparser>=1.0.5
    django-social-auth>=0.7.1,<1.0
      oauth2>=1.5.167
        httplib2
      python-openid>=2.2
    django-social-auth-trello>=1.0.2
  ===> Compiling pinned versions
  sentry==5.0.13
    cssutils==0.9.10b1
    BeautifulSoup==3.2.1
    django-celery==3.0.11
    celery==3.0.11
      billiard==2.7.3.17
      kombu==2.4.7
        anyjson==0.3.3
        amqplib==1.0.2
    django-crispy-forms==1.2.0
    Django==1.4.1
    django-indexer==0.3.0
    django-paging==0.2.4
    django-picklefield==0.2.1
    django-templatetag-sugar==0.1
    gunicorn==0.14.6
    logan==0.5.0
    pynliner==0.4.0
    python-dateutil==1.5
    raven==2.0.6
    South==0.7.6
    httpagentparser==1.1.3
    django-social-auth==0.7.6
      oauth2==1.5.211
        httplib2==0.7.6
      python-openid==2.2.5
    django-social-auth-trello==1.0.2
  ===> Writing out requirements.txt
  amqplib==1.0.2
  anyjson==0.3.3
  BeautifulSoup==3.2.1
  billiard==2.7.3.17
  celery==3.0.11
  cssutils==0.9.10b1
  django-celery==3.0.11
  django-crispy-forms==1.2.0
  django-indexer==0.3.0
  django-paging==0.2.4
  django-picklefield==0.2.1
  django-social-auth-trello==1.0.2
  django-social-auth==0.7.6
  django-templatetag-sugar==0.1
  Django==1.4.1
  gunicorn==0.14.6
  httpagentparser==1.1.3
  httplib2==0.7.6
  kombu==2.4.7
  logan==0.5.0
  oauth2==1.5.211
  pynliner==0.4.0
  python-dateutil==1.5
  python-openid==2.2.5
  raven==2.0.6
  sentry==5.0.13
  South==0.7.6

...
