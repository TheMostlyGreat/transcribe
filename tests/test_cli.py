"""Tests for the CLI functionality."""
import os
import sys
import logging
from pathlib import Path
from unittest import mock

import pytest

# Add parent directory to sys.path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from transcribe.cli import (
    setup_logging,
    display_supported_formats, 
    parse_args, 
    cli_main,
    cleanup_old_logs
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
    
    assert formats
    assert isinstance(formats, str)
    assert all(ext in formats for ext in ["mp3", "wav", "mp4", "mov"])


def test_parse_args():
    """Test command-line argument parsing."""
    # Test file command
    args = parse_args(["file", "test.mp3"])
    assert args.command == "file"
    assert args.media_file == "test.mp3"
    assert not args.verbose
    
    # Test file command with options - verbose must come before the command
    args = parse_args(["--verbose", "file", "test.mp3", "--output", "output.md"])
    assert args.command == "file"
    assert args.media_file == "test.mp3"
    assert args.output == "output.md"
    assert args.verbose

    # Test batch command
    args = parse_args(["batch", "/test/directory"])
    assert args.command == "batch"
    assert args.directory == "/test/directory"
    assert not args.email
    
    # Test batch command with options - verbose must come before the command
    args = parse_args(["--verbose", "batch", "/test/directory", "--email"])
    assert args.command == "batch"
    assert args.directory == "/test/directory"
    assert args.email
    assert args.verbose


@mock.patch("transcribe.cli.transcribe_audio_file")
def test_cli_main_file_command(mock_transcribe, test_audio_file, temp_dir):
    """Test the CLI main function with file command."""
    # Success case
    output_path = temp_dir / "test_output.md"
    mock_transcribe.return_value = output_path
    
    assert cli_main(["file", str(test_audio_file)]) == 0
    mock_transcribe.assert_called_with(str(test_audio_file), output_path=None)
    
    # With custom output path
    assert cli_main(["file", str(test_audio_file), "--output", str(output_path)]) == 0
    mock_transcribe.assert_called_with(str(test_audio_file), output_path=str(output_path))
    
    # Failure case
    mock_transcribe.return_value = None
    assert cli_main(["file", str(test_audio_file)]) == 1


@mock.patch("transcribe.cli.process_folder")
def test_cli_main_batch_command(mock_process, temp_batch_dir):
    """Test the CLI main function with batch command."""
    # Success case
    mock_process.return_value = (True, 3)
    
    assert cli_main(["batch", str(temp_batch_dir)]) == 0
    mock_process.assert_called_with(str(temp_batch_dir), send_emails=False)
    
    # With email option
    assert cli_main(["batch", str(temp_batch_dir), "--email"]) == 0
    mock_process.assert_called_with(str(temp_batch_dir), send_emails=True)
    
    # Failure case
    mock_process.return_value = (False, 1)
    assert cli_main(["batch", str(temp_batch_dir)]) == 1


@mock.patch("transcribe.cli.parse_args")
def test_cli_main_edge_cases(mock_parse_args):
    """Test edge cases for the CLI main function."""
    # No command
    mock_parse_args.return_value = mock.Mock(command=None, verbose=False)
    assert cli_main([]) == 1
    
    # Invalid command
    mock_parse_args.return_value = mock.Mock(command="invalid", verbose=False)
    assert cli_main(["invalid"]) == 1


def test_cleanup_old_logs(temp_dir):
    """Test cleanup of old log files."""
    # Create some mock log files with different ages
    log_dir = temp_dir / "logs"
    log_dir.mkdir()
    
    # Current log
    current_log = log_dir / "transcribe.log"
    current_log.write_text("Current log")
    
    # Create an old log file
    old_log = log_dir / "transcribe_old.log"
    old_log.write_text("Old log")
    
    # Test log cleanup
    with mock.patch('pathlib.Path.stat') as mock_stat:
        # Mock file stats to simulate old files
        mock_stat.return_value.st_mtime = 0  # Very old timestamp
        
        cleanup_old_logs(log_dir)  # Pass log_dir directly 