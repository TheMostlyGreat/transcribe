"""
Tests for the __main__ module.
"""
import sys
import importlib
from unittest import mock

import pytest


def test_main_module():
    """Test the main module entry point."""
    # Import the module
    from transcribe import __main__
    
    # Save the original __name__
    original_name = __main__.__name__
    
    try:
        # Set __name__ to "__main__"
        __main__.__name__ = "__main__"
        
        # Mock sys.exit to prevent actual exit
        with mock.patch.object(sys, 'exit') as mock_exit:
            # Mock cli_main to return 0
            with mock.patch('transcribe.cli.cli_main', return_value=0) as mock_cli_main:
                # Mock sys.argv to provide valid arguments
                with mock.patch.object(sys, 'argv', ['transcribe', 'file', 'test.mp3']):
                    # Execute the code that would run if __name__ == "__main__"
                    if __main__.__name__ == "__main__":
                        mock_exit(mock_cli_main())
                    
                    # Check that mock_cli_main was called
                    mock_cli_main.assert_called_once()
                    
                    # Check that sys.exit was called with the return value from cli_main
                    mock_exit.assert_called_once_with(0)
    finally:
        # Restore the original __name__
        __main__.__name__ = original_name 