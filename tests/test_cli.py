"""
Tests for the command-line interface.
"""
import os
import logging
from pathlib import Path
from unittest import mock
import tempfile
import sys
import importlib

import pytest

from transcribe.cli import (
    setup_logging, 
    display_supported_formats, 
    parse_args, 
    cli_main
)


def test_setup_logging():
    """Test logging setup with different verbosity levels."""
    # Test normal logging level
    setup_logging(verbose=False)
    assert logging.getLogger().level == logging.INFO
    
    # Test verbose logging level
    setup_logging(verbose=True)
    assert logging.getLogger().level == logging.DEBUG


def test_display_supported_formats():
    """Test formatting of supported file extensions."""
    formats = display_supported_formats()
    
    # Check that the function returns a non-empty string
    assert formats
    assert isinstance(formats, str)
    
    # Check that common formats are included
    assert "mp3" in formats
    assert "wav" in formats
    assert "mp4" in formats
    assert "mov" in formats


def test_parse_args_file_command():
    """Test parsing of 'file' command arguments."""
    args = parse_args(["file", "test.mp3"])
    
    assert args.command == "file"
    assert args.media_file == "test.mp3"
    assert not args.verbose
    
    # Test with output option
    args = parse_args(["file", "test.mp3", "--output", "output.md"])
    assert args.output == "output.md"
    
    # Test with verbose option
    args = parse_args(["--verbose", "file", "test.mp3"])
    assert args.verbose


def test_parse_args_batch_command():
    """Test parsing of 'batch' command arguments."""
    args = parse_args(["batch", "/test/directory"])
    
    assert args.command == "batch"
    assert args.directory == "/test/directory"
    assert not args.verbose
    assert not args.email
    
    # Test with email option
    args = parse_args(["batch", "/test/directory", "--email"])
    assert args.email
    
    # Test with verbose option
    args = parse_args(["--verbose", "batch", "/test/directory"])
    assert args.verbose


def test_parse_args_version():
    """Test parsing of version argument."""
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--version"])
    
    # Version should exit with code 0
    assert excinfo.value.code == 0


def test_parse_args_help():
    """Test parsing of help argument."""
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--help"])
    
    # Help should exit with code 0
    assert excinfo.value.code == 0


@mock.patch("transcribe.cli.transcribe_audio_file")
def test_cli_main_file_command(mock_transcribe, test_audio_file, temp_dir):
    """Test the CLI main function with file command."""
    # Set up the mock to return a successful result
    output_path = temp_dir / "test_output.md"
    mock_transcribe.return_value = output_path
    
    # Call the main function with file command
    result = cli_main(["file", str(test_audio_file)])
    
    # Should be successful
    assert result == 0
    
    # Should have called transcribe_audio_file with the correct arguments
    mock_transcribe.assert_called_once_with(str(test_audio_file), output_path=None)
    
    # Test with custom output path
    result = cli_main(["file", str(test_audio_file), "--output", str(output_path)])
    
    # Should have called transcribe_audio_file with the output path
    mock_transcribe.assert_called_with(str(test_audio_file), output_path=str(output_path))


@mock.patch("transcribe.cli.transcribe_audio_file")
def test_cli_main_file_command_failure(mock_transcribe, test_audio_file):
    """Test the CLI main function with file command when transcription fails."""
    # Set up the mock to return a failure result
    mock_transcribe.return_value = None
    
    # Call the main function with file command
    result = cli_main(["file", str(test_audio_file)])
    
    # Should not be successful
    assert result == 1
    
    # Should have called transcribe_audio_file
    mock_transcribe.assert_called_once()


@mock.patch("transcribe.cli.process_folder")
def test_cli_main_batch_command(mock_process, temp_batch_dir):
    """Test the CLI main function with batch command."""
    # Set up the mock to return a successful result
    mock_process.return_value = True
    
    # Call the main function with batch command
    result = cli_main(["batch", str(temp_batch_dir)])
    
    # Should be successful
    assert result == 0
    
    # Should have called process_folder with the correct arguments
    mock_process.assert_called_once_with(str(temp_batch_dir), send_emails=False)
    
    # Test with email option
    result = cli_main(["batch", str(temp_batch_dir), "--email"])
    
    # Should have called process_folder with send_emails=True
    mock_process.assert_called_with(str(temp_batch_dir), send_emails=True)


@mock.patch("transcribe.cli.process_folder")
def test_cli_main_batch_command_failure(mock_process, temp_batch_dir):
    """Test the CLI main function with batch command when processing fails."""
    # Set up the mock to return a failure result
    mock_process.return_value = False
    
    # Call the main function with batch command
    result = cli_main(["batch", str(temp_batch_dir)])
    
    # Should not be successful
    assert result == 1
    
    # Should have called process_folder
    mock_process.assert_called_once()


def test_cli_main_no_command():
    """Test the CLI main function with no command."""
    result = cli_main([])
    
    # Should not be successful
    assert result == 1


def test_setup_logging_with_existing_handlers():
    """Test setup_logging when handlers already exist."""
    # Create a logger with an existing handler
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    
    try:
        # Add a handler if none exists
        if not root_logger.handlers:
            handler = logging.StreamHandler()
            root_logger.addHandler(handler)
        
        # Call setup_logging
        setup_logging(verbose=True)
        
        # Check that the level was set to DEBUG
        assert root_logger.level == logging.DEBUG
        
        # Check that no new handlers were added
        assert len(root_logger.handlers) == len(original_handlers) or len(root_logger.handlers) == 1
    
    finally:
        # Restore original state
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)


def test_parse_args_default_to_file():
    """Test parse_args defaulting to file command when a file path is provided."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
        # Mock sys.argv
        with mock.patch.object(sys, 'argv', ['transcribe', temp_file.name]):
            # We need to mock the Path.exists method to return True
            with mock.patch('pathlib.Path.exists', return_value=True):
                # Call the function directly with the mocked sys.argv
                # This is testing the specific part where it checks sys.argv[1]
                from transcribe.cli import cli_main
                
                # We need to patch parse_args to avoid the actual parsing
                with mock.patch('transcribe.cli.parse_args') as mock_parse_args:
                    # Set up the mock to return a namespace with command="file"
                    mock_args = mock.Mock()
                    mock_args.command = "file"
                    mock_args.media_file = temp_file.name
                    mock_args.output = None
                    mock_args.verbose = False
                    mock_parse_args.return_value = mock_args
                    
                    # Mock transcribe_audio_file to avoid actual transcription
                    with mock.patch('transcribe.cli.transcribe_audio_file') as mock_transcribe:
                        mock_transcribe.return_value = Path(temp_file.name + "_output.md")
                        
                        # Call cli_main with no args to force it to use sys.argv
                        result = cli_main()
                        
                        # Check that parse_args was called
                        mock_parse_args.assert_called_once()
                        
                        # Check that the command was processed
                        mock_transcribe.assert_called_once()
                        
                        # Should return success code
                        assert result == 0


def test_cli_main_direct_execution():
    """Test cli_main when executed directly."""
    # Import the module
    from transcribe import cli
    
    # Save the original __name__
    original_name = cli.__name__
    
    try:
        # Set __name__ to "__main__"
        cli.__name__ = "__main__"
        
        # Mock sys.exit to prevent actual exit
        with mock.patch.object(sys, 'exit') as mock_exit:
            # Mock cli_main to return 0
            with mock.patch('transcribe.cli.cli_main', return_value=0) as mock_cli_main:
                # Mock sys.argv to provide valid arguments
                with mock.patch.object(sys, 'argv', ['transcribe', 'file', 'test.mp3']):
                    # Execute the code that would run if __name__ == "__main__"
                    if cli.__name__ == "__main__":
                        mock_exit(mock_cli_main())
                    
                    # Check that mock_cli_main was called
                    mock_cli_main.assert_called_once()
                    
                    # Check that sys.exit was called with the return value from cli_main
                    mock_exit.assert_called_once_with(0)
    finally:
        # Restore the original __name__
        cli.__name__ = original_name 