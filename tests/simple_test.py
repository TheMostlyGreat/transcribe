"""
A simple test file to verify pytest is working correctly.
"""
import pytest

@pytest.mark.unit
def test_simple():
    """A very simple test that should always pass."""
    assert True

@pytest.mark.unit
def test_math():
    """Test basic math operations."""
    assert 1 + 1 == 2
    assert 2 * 3 == 6 