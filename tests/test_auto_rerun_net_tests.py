import pytest
import random


@pytest.mark.network
def test_flaky():
    assert random.choice([True, False])
