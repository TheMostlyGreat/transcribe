"""
Tests for the package __init__ module.
"""
import sys
from unittest import mock

import pytest

from transcribe import __version__, main


def test_version():
    """Test that the version is a string."""
    assert isinstance(__version__, str)
    assert __version__ != ""


def test_main_function():
    """Test the main function entry point."""
    # Mock cli_main to prevent actual execution
    with mock.patch('transcribe.cli.cli_main', return_value=0) as mock_cli_main:
        # Call the main function
        main()
        
        # Check that cli_main was called
        mock_cli_main.assert_called_once() 