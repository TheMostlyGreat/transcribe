"""Tests for the batch processing functionality."""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# Add parent directory to sys.path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from transcribe.batch import (
    get_email_config, 
    validate_email_config, 
    send_email_alert, 
    find_new_media_files, 
    process_folder
)


def test_get_email_config(mock_env_vars):
    """Test retrieving email configuration from environment."""
    config = get_email_config()
    assert config["smtp_server"] == "localhost"
    assert config["smtp_port"] == 587
    assert config["smtp_username"] == "test"
    assert config["email_from"] == "from@example.com"


def test_validate_email_config():
    """Test email configuration validation."""
    # Valid configuration
    valid_config = {
        "smtp_server": "localhost",
        "smtp_port": 587,
        "smtp_username": "test",
        "smtp_password": "test",
        "email_from": "from@example.com",
        "email_to": "to@example.com"
    }
    assert validate_email_config(valid_config) is True
    
    # Invalid configuration (missing field)
    invalid_config = valid_config.copy()
    del invalid_config["smtp_username"]
    assert validate_email_config(invalid_config) is False


@mock.patch("transcribe.batch.smtplib.SMTP")
def test_send_email_alert(mock_smtp, test_audio_file, temp_dir, mock_env_vars):
    """Test sending email notification - success and failure cases."""
    # Create mock transcription file
    transcription_file = temp_dir / "test_transcription.md"
    transcription_file.write_text("Test transcription")
    
    # Test successful email sending
    mock_smtp_instance = mock.Mock()
    mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
    
    assert send_email_alert(test_audio_file, transcription_file) is True
    mock_smtp.assert_called_with("localhost", 587)
    mock_smtp_instance.send_message.assert_called_once()
    
    # Test failure case
    mock_smtp.reset_mock()
    mock_smtp.return_value.__enter__.side_effect = Exception("SMTP error")
    assert send_email_alert(test_audio_file, transcription_file) is False
    
    # Test invalid config
    with mock.patch.dict(os.environ, clear=True):
        assert send_email_alert(test_audio_file, transcription_file) is False


def test_find_new_media_files(temp_batch_dir):
    """Test finding new media files in a directory."""
    # Initially all files are new
    new_files = find_new_media_files(str(temp_batch_dir))
    assert len(new_files) == 3
    
    # Create transcription for one file
    test_file = temp_batch_dir / "test_audio_0.mp3"
    transcription_file = temp_batch_dir / "test_audio_0_transcription.md"
    transcription_file.write_text("Test transcription")
    
    # Now should find only 2 new files
    new_files = find_new_media_files(str(temp_batch_dir))
    assert len(new_files) == 2
    
    # Test non-existent directory
    assert find_new_media_files("/nonexistent/directory") == []


def create_mock_transcriber():
    """Helper to create a consistent mock for transcribe_audio_file."""
    def side_effect(path, output_path=None, retry_existing=False):
        file_path = Path(path)
        if output_path is None:
            output_path = file_path.with_name(f"{file_path.stem}_transcription.md")
        else:
            output_path = Path(output_path)
        
        output_path.write_text("Mock transcription")
        return output_path
    return side_effect


def test_process_folder_scenarios(temp_batch_dir, mock_env_vars):
    """Test various folder processing scenarios."""
    # Create a fresh batch directory for each scenario to avoid state between tests
    # 1. Process all files successfully
    with mock.patch("transcribe.batch.find_new_media_files") as mock_find_files:
        with mock.patch("transcribe.batch.transcribe_audio_file") as mock_transcribe:
            # Setup mock to return 3 files
            mock_find_files.return_value = [
                (temp_batch_dir / f"test_audio_{i}.mp3", None) for i in range(3)
            ]
            # Setup transcription mock
            mock_transcribe.side_effect = create_mock_transcriber()
            
            success, count = process_folder(str(temp_batch_dir))
            assert success is True
            assert count == 3
            assert mock_transcribe.call_count == 3
    
    # 2. Process with email notifications
    with mock.patch("transcribe.batch.find_new_media_files") as mock_find_files:
        with mock.patch("transcribe.batch.transcribe_audio_file") as mock_transcribe:
            with mock.patch("transcribe.batch.send_email_alert") as mock_email:
                # Setup mock to return 3 files
                mock_find_files.return_value = [
                    (temp_batch_dir / f"test_audio_{i}.mp3", None) for i in range(3)
                ]
                mock_transcribe.side_effect = create_mock_transcriber()
                mock_email.return_value = True
                
                success, count = process_folder(str(temp_batch_dir), send_emails=True)
                assert success is True
                assert count == 3
                assert mock_email.call_count == 3
    
    # 3. Process with some failures
    with mock.patch("transcribe.batch.find_new_media_files") as mock_find_files:
        with mock.patch("transcribe.batch.transcribe_audio_file") as mock_transcribe:
            # Setup mock to return 3 files
            mock_find_files.return_value = [
                (temp_batch_dir / f"test_audio_{i}.mp3", None) for i in range(3)
            ]
            
            # Set up partial failure for test_audio_1.mp3
            def partial_failure(path, output_path=None, retry_existing=False):
                if "test_audio_1.mp3" in str(path):
                    return None
                return create_mock_transcriber()(path, output_path, retry_existing)
            
            mock_transcribe.side_effect = partial_failure
            success, count = process_folder(str(temp_batch_dir))
            assert success is False
            assert count == 2
    
    # 4. Empty folder
    with mock.patch("transcribe.batch.find_new_media_files") as mock_find_files:
        with mock.patch("transcribe.batch.transcribe_audio_file") as mock_transcribe:
            # No files to process
            mock_find_files.return_value = []
            
            success, count = process_folder(str(temp_batch_dir))
            assert success is True
            assert count == 0
            mock_transcribe.assert_not_called() 