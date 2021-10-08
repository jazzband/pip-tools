import pytest

from piptools.repositories.local import LocalRequirementsRepository
from piptools.utils import key_from_ireq

EXPECTED = {"sha256:5e6071ee6e4c59e0d0408d366fe9b66781d2cf01be9a6e19a2433bb3c5336330"}


def test_get_hashes_local_repository_cache_miss(
    capsys, pip_conf, from_line, pypi_repository
):
    existing_pins = {}
    local_repository = LocalRequirementsRepository(existing_pins, pypi_repository)
    with local_repository.allow_all_wheels():
        hashes = local_repository.get_hashes(from_line("small-fake-a==0.1"))
        assert hashes == EXPECTED
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_get_hashes_local_repository_cache_hit(from_line, repository):
    # Create an install requirement with the hashes included in its options
    options = {"hashes": {"sha256": [entry.split(":")[1] for entry in EXPECTED]}}
    req = from_line("small-fake-a==0.1", options=options)
    existing_pins = {key_from_ireq(req): req}

    # Use fake repository so that we know the hashes are coming from cache
    local_repository = LocalRequirementsRepository(existing_pins, repository)
    with local_repository.allow_all_wheels():
        hashes = local_repository.get_hashes(from_line("small-fake-a==0.1"))
        assert hashes == EXPECTED


NONSENSE = {"sha256:NONSENSE"}


@pytest.mark.parametrize(
    ("reuse_hashes", "expected"), ((True, NONSENSE), (False, EXPECTED))
)
def test_toggle_reuse_hashes_local_repository(
    capsys, pip_conf, from_line, pypi_repository, reuse_hashes, expected
):
    # Create an install requirement with the hashes included in its options
    options = {"hashes": {"sha256": [entry.split(":")[1] for entry in NONSENSE]}}
    req = from_line("small-fake-a==0.1", options=options)
    existing_pins = {key_from_ireq(req): req}

    local_repository = LocalRequirementsRepository(
        existing_pins, pypi_repository, reuse_hashes=reuse_hashes
    )
    with local_repository.allow_all_wheels():
        assert local_repository.get_hashes(from_line("small-fake-a==0.1")) == expected
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
