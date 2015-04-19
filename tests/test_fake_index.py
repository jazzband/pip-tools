from pytest import raises


def test_find_best_match(from_line, repository):
    ireq = from_line('django>1.5')
    assert repository.find_best_match(ireq) == '1.8'
    ireq = from_line('django<1.8,~=1.6')
    assert repository.find_best_match(ireq) == '1.7.7'


def test_find_best_match_for_editable(from_editable, repository):
    ireq = from_editable('git+git://whatev.org/blah.git#egg=flask')
    assert repository.find_best_match(ireq) == ireq


def test_get_dependencies(from_line, repository):
    ireq = from_line('django==1.6.11')
    assert repository.get_dependencies(ireq) == []

    ireq = from_line('Flask==0.10.1')
    assert (set(repository.get_dependencies(ireq)) ==
            {'Werkzeug>=0.7', 'Jinja2>=2.4', 'itsdangerous>=0.21'})


def test_get_dependencies_for_editable(from_editable, repository):
    ireq = from_editable('git+git://example.org/django.git#egg=django')
    assert repository.get_dependencies(ireq) == []


def test_get_dependencies_rejects_non_pinned_requirements(from_line, repository):
    not_a_pinned_req = from_line('django>1.6')
    with raises(TypeError):
        repository.get_dependencies(not_a_pinned_req)
