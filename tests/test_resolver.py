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

        (['SQLAlchemy'],
         ['sqlalchemy==0.9.9']),

        (['SQLAlchemy'],
         ['sqlalchemy==1.0.0b5'],
         True),

    ])
)
def test_resolver(resolver, from_line, input, expected, prereleases):
    input = [from_line(line) for line in input]
    output = resolver(input, prereleases=prereleases).resolve()
    output = {str(line) for line in output}
    assert output == {str(line) for line in expected}
