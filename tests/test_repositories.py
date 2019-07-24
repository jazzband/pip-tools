import pytest
from mock import MagicMock, patch

from piptools._compat import PackageFinder, install_req_from_line
from piptools.utils import PIP_VERSION


def test_pypirepo_build_dir_is_str(pypi_repository):
    assert isinstance(pypi_repository.build_dir, str)


def test_pypirepo_source_dir_is_str(pypi_repository):
    assert isinstance(pypi_repository.source_dir, str)


@pytest.mark.skipif(
    PIP_VERSION >= (10,),
    reason="RequirementSet objects don't take arguments after pip 10.",
)
def test_pypirepo_calls_reqset_with_str_paths(pypi_repository):
    """
    Make sure that paths passed to RequirementSet init are str.

    Passing unicode paths on Python 2 could make pip fail later on
    unpack, if the package contains non-ASCII file names, because
    non-ASCII str and unicode paths cannot be combined.
    """
    with patch("piptools.repositories.pypi.RequirementSet") as mocked_init:
        ireq = install_req_from_line("ansible==2.4.0.0")

        # Setup a mock object to be returned from the RequirementSet call
        mocked_reqset = MagicMock()
        mocked_init.return_value = mocked_reqset

        # Do the call
        pypi_repository.get_dependencies(ireq)

        # Check that RequirementSet init is called with correct type arguments
        assert mocked_init.call_count == 1
        (init_call_args, init_call_kwargs) = mocked_init.call_args
        assert isinstance(init_call_args[0], str)
        assert isinstance(init_call_args[1], str)
        assert isinstance(init_call_kwargs.get("download_dir"), str)
        assert isinstance(init_call_kwargs.get("wheel_download_dir"), str)

        # Check that _prepare_file is called correctly
        assert mocked_reqset._prepare_file.call_count == 1
        (pf_call_args, pf_call_kwargs) = mocked_reqset._prepare_file.call_args
        (called_with_finder, called_with_ireq) = pf_call_args
        assert isinstance(called_with_finder, PackageFinder)
        assert called_with_ireq == ireq
        assert not pf_call_kwargs
