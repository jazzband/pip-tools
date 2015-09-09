import pytest


@pytest.mark.parametrize(
    ('input', 'expected', 'prereleases'),

    ((tup + (False,))[:3] for tup in [

        (['Django'], ['django==1.8']),

        (['Flask'],
         ['flask==0.10.1', 'itsdangerous==0.24', 'markupsafe==0.23',
         'jinja2==2.7.3', 'werkzeug==0.10.4']),

        (['Jinja2', 'markupsafe'],
         ['jinja2==2.7.3', 'markupsafe==0.23']),

        # We should return a normal release version if prereleases is False
        (['SQLAlchemy'],
         ['sqlalchemy==0.9.9']),

        # We should return the prerelease version if prereleases is True
        (['SQLAlchemy'],
         ['sqlalchemy==1.0.0b5'],
         True),

        # Ipython has extras available, but we don't require them in this test
        (['ipython'],
         ['ipython==2.1.0', 'gnureadline==6.3.3']),

        # We should get dependencies for extras
        (['ipython[notebook]'],
         [
             'ipython[notebook]==2.1.0',
             'pyzmq==2.1.12',
             'jinja2==2.7.3',
             'tornado==3.2.2',
             'markupsafe==0.23',
             'gnureadline==6.3.3']
         ),

        # We should get dependencies for multiple extras
        (['ipython[notebook,nbconvert]'],
         [
             # Note that the extras should be sorted
             'ipython[nbconvert,notebook]==2.1.0',
             'pyzmq==2.1.12',
             'jinja2==2.7.3',
             'tornado==3.2.2',
             'markupsafe==0.23',
             'gnureadline==6.3.3',
             'pygments==1.5',
             'sphinx==0.3']
         ),

        # We must take the union of all extras
        (['ipython[notebook]', 'ipython[nbconvert]'],
         [
             # Note that the extras should be sorted
             'ipython[nbconvert,notebook]==2.1.0',
             'pyzmq==2.1.12',
             'jinja2==2.7.3',
             'tornado==3.2.2',
             'markupsafe==0.23',
             'gnureadline==6.3.3',
             'pygments==1.5',
             'sphinx==0.3']
         ),
    ])
)
def test_resolver(resolver, from_line, input, expected, prereleases):
    input = [from_line(line) for line in input]
    output = resolver(input, prereleases=prereleases).resolve()
    output = {str(line) for line in output}
    assert output == {str(line) for line in expected}
