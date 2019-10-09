import pytest

@pytest.mark.network
def test_always_fails():
    assert False
