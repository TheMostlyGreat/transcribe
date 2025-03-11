"""Tests for package imports and structure."""
import sys
import importlib
import pytest
import os
from pathlib import Path


@pytest.mark.unit
def test_package_importable():
    """Test that the package can be imported."""
    try:
        import transcribe
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import transcribe package: {e}")


@pytest.mark.unit
def test_version_available():
    """Test that the version is properly defined and accessible."""
    import transcribe
    assert hasattr(transcribe, '__version__')
    assert transcribe.__version__ == "0.1"


@pytest.mark.unit
@pytest.mark.parametrize("module_name,expected_attrs", [
    ("core", ["transcribe_audio_file", "is_supported_file", "get_media_type", "SUPPORTED_EXTENSIONS"]),
    ("batch", ["process_folder"]),
    ("cli", ["cli_main", "parse_args", "setup_logging"])
])
def test_module_structure(module_name, expected_attrs):
    """Test that modules have the expected attributes and functions."""
    # Import the module
    module = importlib.import_module(f"transcribe.{module_name}")
    
    # Check expected attributes exist
    for attr_name in expected_attrs:
        assert hasattr(module, attr_name)
        
        # If it's a function (not a constant), check it's callable
        attr = getattr(module, attr_name)
        if not attr_name.isupper():  # Constants are typically UPPERCASE
            assert callable(attr)
    
    # Check SUPPORTED_EXTENSIONS in core module
    if module_name == "core" and hasattr(module, "SUPPORTED_EXTENSIONS"):
        assert isinstance(module.SUPPORTED_EXTENSIONS, set)
        assert len(module.SUPPORTED_EXTENSIONS) > 0 