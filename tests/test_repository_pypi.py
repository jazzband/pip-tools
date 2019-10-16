import mock
import pytest

from piptools._compat.pip_compat import Link, Session, path_to_url
from piptools.repositories.pypi import open_local_or_remote_file


@pytest.mark.network
def test_generate_hashes_all_platforms(from_line, pypi_repository):
    expected = {
        "sha256:04b133ef629ae2bc05f83d0b079a964494a9cd17914943e690c57209b44aae20",
        "sha256:0f1b3193c17b93c75e73eeac92f22eec4c98a021d9969b1c347d1944fae0d26b",
        "sha256:1fb1cf40c315656f98f4d3acfb1bd031a14a9a69d155e9a180d5f9b52eaf745a",
        "sha256:20af85d8e154b50f540bc8d517a0dbf6b1c20b5d06e572afda919d5dafd1d06b",
        "sha256:2570f93b42c61013ab4b26e23aa25b640faf5b093ad7dd3504c3a8eadd69bc24",
        "sha256:2f4e2872833ee3764dfc168dea566b7dd83b01ac61b377490beba53b5ece57f7",
        "sha256:31776a37a67424e7821324b9e03a05aa6378bbc2bccc58fa56402547f82803c6",
        "sha256:353421c76545f1d440cacc137abc865f07eab9df0dd3510c0851a2ca04199e90",
        "sha256:36d06de7b09b1eba54b1f5f76e2221afef7489cc61294508c5a7308a925a50c6",
        "sha256:3f1908d0bcd654f8b7b73204f24336af9f020b707fb8af937e3e2279817cbcd6",
        "sha256:5268de3a18f031e9787c919c1b9137ff681ea696e76740b1c6c336a26baaa58a",
        "sha256:563e0bd53fda03c151573217b3a49b3abad8813de9dd0632e10090f6190fdaf8",
        "sha256:5e1368d13f1774852f9e435260be19ad726bbfb501b80472f61c2dc768a0692a",
        "sha256:60881c79eb72cb75bd0a4be5e31c9e431739146c4184a2618cabea3938418984",
        "sha256:6120b62a642a40e47eb6c9ff00c02be69158fc7f7c5ff78e42a2c739d1c57cd6",
        "sha256:65c223e77f87cb463191ace3398e0a6d84ce4ac575d42eb412a220b099f593d6",
        "sha256:6fbf8db55710959344502b58ab937424173ad8b5eb514610bcf56b119caa350a",
        "sha256:74aadea668c94eef4ceb09be3d0eae6619e28b4f1ced4e29cd43a05bb2cfd7a4",
        "sha256:7be1efa623e1ed91b15b1e62e04c536def1d75785eb930a0b8179ca6b65ed16d",
        "sha256:83266cdede210393889471b0c2631e78da9d4692fcca875af7e958ad39b897ee",
        "sha256:86c68a3f8246495962446c6f96f6a27f182b91208187b68f1e87ec3dfd29fa32",
        "sha256:9163f7743cf9991edaddf9cf886708e288fab38e1b9fec9c41c15c85c8f7f147",
        "sha256:97d9f338f91b7927893ea6500b953e4b4b7e47c6272222992bb76221e17056ff",
        "sha256:a7930e73a4359b52323d09de6d6860840314aa09346cbcf4def8875e1b07ebc7",
        "sha256:ada8a42c493e4934a1a8875c2bc9efcb1b88c09883f70375bfa053ab32d6a118",
        "sha256:b0bc2d83cc0ba0e8f0d9eca2ffe07f72f33bec7d84547071e7e875d4cca8272d",
        "sha256:b5412a65605c642adf3e1544b59b8537daf5696dedadd2b3cbebc42e24da45ed",
        "sha256:ba6b5205fced1625b6d9d55f9ef422f9667c5d95f18f07c0611eb964a3355331",
        "sha256:bcaf3d86385daaab0ae51c9c53ebe70a6c1c5dfcb9e311b13517e04773ddf6b6",
        "sha256:cfa15570ecec1ea6bee089e86fd4deae6208c96a811344ce246de5e5c9ac824a",
        "sha256:d3e3063af1fa6b59e255da9a812891cdaf24b90fbaf653c02797871069b7c4c9",
        "sha256:d9cfe26ecea2fec320cd0cac400c9c2435328994d23596ee6df63945fe7292b0",
        "sha256:e5ef800ef8ef9ee05ae9a5b7d7d9cf7d6c936b32e312e54823faca3034ee16ab",
        "sha256:f1366150acf611d09d37ffefb3559ed3ffeb1713643d3cd10716d6c5da3f83fb",
        "sha256:f4eb9747a37120b35f59c8e96265e87b0c432ff010d32fc0772992aa14659502",
        "sha256:f8264463cc08cd696ad17e4bf3c80f3344628c04c11ffdc545ddf0798bc17316",
        "sha256:f8ba54848dfe280b1be0d6e699544cee4ba10d566f92464538063d9e645aed3e",
        "sha256:f93d1edcaea7b6a7a8fbf936f4492a9a0ee0b4cb281efebd5e1dd73e5e432c71",
        "sha256:fc8865c7e0ac25ddd71036c2b9a799418b32d9acb40400d345b8791b6e1058cb",
        "sha256:fce6b0cb9ade1546178c031393633b09c4793834176496c99a94de0bfa471b27",
        "sha256:fde17c52d7ce7d55a9fb263b57ccb5da6439915b5c7105617eb21f636bb1bd9c",
    }

    ireq = from_line("cffi==1.9.1")
    with pypi_repository.allow_all_wheels():
        assert pypi_repository.get_hashes(ireq) == expected


@pytest.mark.network
def test_generate_hashes_without_interfering_with_each_other(
    from_line, pypi_repository
):
    pypi_repository.get_hashes(from_line("cffi==1.9.1"))
    pypi_repository.get_hashes(from_line("matplotlib==2.0.2"))


def test_get_hashes_editable_empty_set(from_editable, pypi_repository):
    ireq = from_editable("git+https://github.com/django/django.git#egg=django")
    assert pypi_repository.get_hashes(ireq) == set()


@pytest.mark.parametrize("content, content_length", [(b"foo", 3), (b"foobar", 6)])
def test_open_local_or_remote_file__local_file(tmp_path, content, content_length):
    """
    Test the `open_local_or_remote_file` returns a context manager to a FileStream
    for a given `Link` to a local file.
    """
    local_file_path = tmp_path / "foo.txt"
    local_file_path.write_bytes(content)

    link = Link(local_file_path.as_uri())
    session = Session()

    with open_local_or_remote_file(link, session) as file_stream:
        assert file_stream.stream.read() == content
        assert file_stream.size == content_length


def test_open_local_or_remote_file__directory(tmpdir):
    """
    Test the `open_local_or_remote_file` raises a ValueError for a given `Link`
    to a directory.
    """
    link = Link(path_to_url(tmpdir.strpath))
    session = Session()

    with pytest.raises(ValueError, match="Cannot open directory for read"):
        with open_local_or_remote_file(link, session):
            pass  # pragma: no cover


@pytest.mark.parametrize(
    "content, content_length, expected_content_length",
    [(b"foo", 3, 3), (b"bar", None, None), (b"kek", "invalid-content-length", None)],
)
def test_open_local_or_remote_file__remote_file(
    tmp_path, content, content_length, expected_content_length
):
    """
    Test the `open_local_or_remote_file` returns a context manager to a FileStream
    for a given `Link` to a remote file.
    """
    link = Link("https://example.com/foo.txt")
    session = Session()

    response_file_path = tmp_path / "foo.txt"
    response_file_path.write_bytes(content)

    mock_response = mock.Mock()
    mock_response.raw = response_file_path.open("rb")
    mock_response.headers = {"content-length": content_length}

    with mock.patch.object(session, "get", return_value=mock_response):
        with open_local_or_remote_file(link, session) as file_stream:
            assert file_stream.stream.read() == content
            assert file_stream.size == expected_content_length

    mock_response.close.assert_called_once()
