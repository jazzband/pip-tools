from __future__ import annotations

import pytest
from pip._internal.exceptions import DistributionNotFound
from pip._internal.utils.urls import path_to_url

from piptools.resolver import RequirementSummary, combine_install_requirements


def test_combine_install_requirements(from_line):
    celery30 = from_line("celery>3.0", comes_from="-r requirements.in")
    celery31 = from_line("celery==3.1.1", comes_from=from_line("fake-package"))
    celery32 = from_line("celery<3.2")

    combined = combine_install_requirements([celery30, celery31])
    assert combined.comes_from == celery31.comes_from  # shortest string
    assert set(combined._source_ireqs) == {celery30, celery31}
    assert str(combined.req.specifier) == "==3.1.1,>3.0"

    combined_all = combine_install_requirements([celery32, combined])
    assert combined_all.comes_from is None
    assert set(combined_all._source_ireqs) == {celery30, celery31, celery32}
    assert str(combined_all.req.specifier) == "<3.2,==3.1.1,>3.0"


def _test_combine_install_requirements_extras(with_extra, without_extra):
    combined = combine_install_requirements([without_extra, with_extra])
    assert str(combined) == str(with_extra)
    assert combined.extras == with_extra.extras

    combined = combine_install_requirements([with_extra, without_extra])
    assert str(combined) == str(with_extra)
    assert combined.extras == with_extra.extras


def test_combine_install_requirements_extras_req(from_line, make_package):
    """
    Extras should be unioned in combined install requirements
    (whether or not InstallRequirement.req is None, and testing either order of the inputs)
    """
    with_extra = from_line("edx-opaque-keys[django]==1.0.1")
    assert with_extra.req is not None
    without_extra = from_line("edx-opaque-keys")
    assert without_extra.req is not None

    _test_combine_install_requirements_extras(with_extra, without_extra)


def test_combine_install_requirements_extras_no_req(from_line, make_package):
    """
    Extras should be unioned in combined install requirements
    (whether or not InstallRequirement.req is None, and testing either order of the inputs)
    """
    test_package = make_package("test-package", extras_require={"extra": []})
    local_package_with_extra = from_line(f"{test_package}[extra]")
    assert local_package_with_extra.req is None
    local_package_without_extra = from_line(path_to_url(test_package))
    assert local_package_without_extra.req is None

    _test_combine_install_requirements_extras(
        local_package_with_extra, local_package_without_extra
    )


def test_combine_install_requirements_with_paths(from_line, make_package):
    name = "fake_package_b"
    version = "1.0.0"

    test_package = make_package(name, version=version)
    fake_package = from_line(f"{name} @ {path_to_url(test_package)}")
    fake_package_name = from_line(f"{name}=={version}", comes_from=from_line(name))

    for pair in [(fake_package, fake_package_name), (fake_package_name, fake_package)]:
        combined = combine_install_requirements(pair)
        assert str(combined.specifier) == str(fake_package_name.specifier)
        assert str(combined.link) == str(fake_package.link)
        assert str(combined.local_file_path) == str(fake_package.local_file_path)
        assert str(combined.original_link) == str(fake_package.original_link)


def test_combine_install_requirements_for_one_package_with_multiple_extras(
    from_line,
):
    """Regression test for https://github.com/jazzband/pip-tools/pull/1512"""
    pkg1 = from_line("ray[default]==1.1.1")
    pkg2 = from_line("ray[tune]==1.1.1")
    combined = combine_install_requirements([pkg1, pkg2])

    assert str(combined) == "ray[default,tune]==1.1.1"


@pytest.mark.parametrize(
    ("left_hand", "right_hand", "expected"),
    (
        ("test_package", "test_package", True),
        ("test_package==1.2.3", "test_package==1.2.3", True),
        ("test_package>=1.2.3", "test_package>=1.2.3", True),
        ("test_package==1.2", "test_package==1.2.0", True),
        ("test_package>=1.2", "test_package>=1.2.0", True),
        ("test_package[foo,bar]==1.2", "test_package[bar,foo]==1.2", True),
        ("test_package[foo,bar]>=1.2", "test_package[bar,foo]>=1.2", True),
        ("test_package[foo,bar]==1.2", "test_package[bar,foo]==1.2.0", True),
        ("test_package[foo,bar]>=1.2", "test_package[bar,foo]>=1.2.0", True),
        ("test_package", "other_test_package", False),
        ("test_package==1.2.3", "other_test_package==1.2.3", False),
        ("test_package==1.2.3", "test_package==1.2.4", False),
        ("test_package>=1.2.3", "test_package>=1.2.4", False),
        ("test_package>=1.2.3", "test_package<=1.2.3", False),
        ("test_package==1.2", "test_package==1.2.3", False),
        ("test_package>=1.2", "test_package>=1.2.3", False),
        ("test_package[foo]==1.2", "test_package[bar]==1.2.0", False),
        ("test_package[foo]>=1.2", "test_package[bar]>=1.2.0", False),
        ("test_package[foo,bar]>=1.2", "test_package[bar]>=1.2.0", False),
        ("test_package[foo,bar]>=1.2", "test_package[bar,zee]>=1.2.0", False),
    ),
)
def test_RequirementSummary_equality(from_line, left_hand, right_hand, expected):
    """
    RequirementSummary should report proper equality.
    """
    lh_summary = RequirementSummary(from_line(left_hand))
    rh_summary = RequirementSummary(from_line(right_hand))
    assert (lh_summary == rh_summary) is expected


@pytest.mark.parametrize(
    ("left_hand", "right_hand", "expected"),
    (
        ("test_package", "test_package", True),
        ("test_package==1.2.3", "test_package==1.2.3", True),
        ("test_package>=1.2.3", "test_package>=1.2.3", True),
        ("test_package==1.2", "test_package==1.2.0", True),
        ("test_package>=1.2", "test_package>=1.2.0", True),
        ("test_package[foo,bar]==1.2", "test_package[bar,foo]==1.2", True),
        ("test_package[foo,bar]>=1.2", "test_package[bar,foo]>=1.2", True),
        ("test_package[foo,bar]==1.2", "test_package[bar,foo]==1.2.0", True),
        ("test_package[foo,bar]>=1.2", "test_package[bar,foo]>=1.2.0", True),
        ("test_package", "other_test_package", False),
        ("test_package==1.2.3", "other_test_package==1.2.3", False),
        ("test_package==1.2.3", "test_package==1.2.4", False),
        ("test_package>=1.2.3", "test_package>=1.2.4", False),
        ("test_package>=1.2.3", "test_package<=1.2.3", False),
        ("test_package==1.2", "test_package==1.2.3", False),
        ("test_package>=1.2", "test_package>=1.2.3", False),
        ("test_package[foo]==1.2", "test_package[bar]==1.2.0", False),
        ("test_package[foo]>=1.2", "test_package[bar]>=1.2.0", False),
        ("test_package[foo,bar]>=1.2", "test_package[bar]>=1.2.0", False),
        ("test_package[foo,bar]>=1.2", "test_package[bar,zee]>=1.2.0", False),
    ),
)
def test_RequirementSummary_hash_equality(from_line, left_hand, right_hand, expected):
    """
    RequirementSummary hash for equivalent requirements should be equal.
    """
    lh_summary = RequirementSummary(from_line(left_hand))
    rh_summary = RequirementSummary(from_line(right_hand))
    assert (hash(lh_summary) == hash(rh_summary)) is expected


def test_requirement_summary_with_other_objects(from_line):
    """
    RequirementSummary should not be equal to any other object
    """
    requirement_summary = RequirementSummary(from_line("test_package==1.2.3"))
    other_object = object()
    assert requirement_summary != other_object


@pytest.mark.parametrize(
    ("exception", "cause"),
    (
        pytest.param(DistributionNotFound, None, id="without cause"),
        pytest.param(DistributionNotFound, ZeroDivisionError, id="with cause"),
    ),
)
def test_catch_distribution_not_found_error(resolver, exception, cause):
    """
    Test internal edge-cases when backtracking resolver catches
    and re-raises ``DistributionNotFound`` error with/without causes.
    """
    resolver_obj = resolver([])

    class FakePipResolver:
        def resolve(self, *args, **kwargs):
            raise exception from cause

    with pytest.raises(DistributionNotFound):
        resolver_obj._do_resolve(
            resolver=FakePipResolver(),
            compatible_existing_constraints={},
        )
