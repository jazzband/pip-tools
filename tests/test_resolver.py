import pytest


@pytest.mark.parametrize(
    ('input', 'expected', 'prereleases', 'no_upgrade', 'existing_dependencies'),

    ((tup + (False, False, None))[:5] for tup in [

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

        (['frobnicator'],
         [
            "frobnicator==1.0.0",
            "widgetizer==2.0.0",
            "flux-capacitor==1.0.0"],
         False,
         True,
         [
            "widgetizer==1.0.0",
            "flux-capacitor==1.0.0"]
        )
    ])
)
def test_resolver(resolver, from_line, input, expected, prereleases, no_upgrade, existing_dependencies):
    input = [from_line(line) for line in input]
    dependency_dict = {}
    if existing_dependencies:
        for line in existing_dependencies:
            ireq = from_line(line)
            dependency_dict[ireq.req.project_name] = ireq
    output = resolver(input, prereleases=prereleases, no_upgrade=no_upgrade, existing_dependencies=dependency_dict).resolve()
    output = {str(line) for line in output}
    assert output == {str(line) for line in expected}
