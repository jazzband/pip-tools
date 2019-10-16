import os

import pytest

from piptools.repositories import PyPIRepository


class MockedPyPIRepository(PyPIRepository):
    def get_dependencies(self, ireq):
        # "mock" everything but editable reqs to avoid disk and network I/O
        # when possible
        if not ireq.editable:
            return set()

        return super(MockedPyPIRepository, self).get_dependencies(ireq)


@pytest.fixture
def mocked_repository():
    return MockedPyPIRepository(["--index-url", PyPIRepository.DEFAULT_INDEX_URL])


@pytest.mark.parametrize(
    ("input", "expected"),
    (
        (tup)
        for tup in [
            (
                [
                    os.path.join(
                        os.path.dirname(__file__),
                        "test_data",
                        "packages",
                        "small_fake_with_deps",
                    )
                ],
                ["six"],
            )
        ]
    ),
)
@pytest.mark.network
def test_editable_top_level_deps_preserved(
    base_resolver, mocked_repository, from_editable, input, expected
):
    input = [from_editable(line) for line in input]
    output = base_resolver(
        input, prereleases=False, repository=mocked_repository
    ).resolve()

    output = {p.name for p in output}

    # sanity check that we're expecting something
    assert output != set()

    for package_name in expected:
        assert package_name in output
