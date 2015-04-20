from pytest import raises


def test_find_best_match(from_line, repository):
    ireq = from_line('django>1.5')
    assert str(repository.find_best_match(ireq)) == 'django==1.8'
    ireq = from_line('django<1.8,~=1.6')
    assert str(repository.find_best_match(ireq)) == 'django==1.7.7'


def test_find_best_match_incl_prereleases(from_line, repository):
    ireq = from_line('SQLAlchemy')
    assert str(repository.find_best_match(ireq, prereleases=False)) == 'sqlalchemy==0.9.9'
    assert str(repository.find_best_match(ireq, prereleases=True)) == 'sqlalchemy==1.0.0b5'


def test_find_best_match_for_editable(from_editable, repository):
    ireq = from_editable('git+git://whatev.org/blah.git#egg=flask')
    assert repository.find_best_match(ireq) == ireq


def test_get_dependencies(from_line, repository):
    ireq = from_line('django==1.6.11')
    assert repository.get_dependencies(ireq) == []

    ireq = from_line('Flask==0.10.1')
    dependencies = repository.get_dependencies(ireq)
    assert (set(str(req) for req in dependencies) ==
            {'Werkzeug>=0.7', 'Jinja2>=2.4', 'itsdangerous>=0.21'})


def test_get_dependencies_for_editable(from_editable, repository):
    ireq = from_editable('git+git://example.org/django.git#egg=django')
    assert repository.get_dependencies(ireq) == []


def test_get_dependencies_rejects_non_pinned_requirements(from_line, repository):
    not_a_pinned_req = from_line('django>1.6')
    with raises(TypeError):
        repository.get_dependencies(not_a_pinned_req)
