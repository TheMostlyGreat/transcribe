"""
Tests for the batch processing functionality.
"""
import os
from pathlib import Path
from unittest import mock

import pytest

from transcribe.batch import (
    get_email_config, 
    validate_email_config, 
    send_email_alert, 
    find_new_media_files, 
    process_folder
)
from tests.mocks import MockAssemblyAI


def test_get_email_config(mock_env_vars):
    """Test retrieving email configuration from environment."""
    config = get_email_config()
    assert config["smtp_server"] == "localhost"
    assert config["smtp_port"] == 587
    assert config["smtp_username"] == "test"
    assert config["smtp_password"] == "test"
    assert config["email_from"] == "from@example.com"
    assert config["email_to"] == "to@example.com"


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
    
    # Invalid configuration (missing required field)
    invalid_config = valid_config.copy()
    invalid_config["smtp_server"] = None
    assert validate_email_config(invalid_config) is False
    
    # Invalid configuration (missing field)
    invalid_config = valid_config.copy()
    del invalid_config["smtp_username"]
    assert validate_email_config(invalid_config) is False


@mock.patch("transcribe.batch.smtplib.SMTP")
def test_send_email_alert(mock_smtp, test_audio_file, temp_dir, mock_env_vars):
    """Test sending email notification."""
    # Create mock transcription file
    transcription_file = temp_dir / "test_transcription.md"
    transcription_file.write_text("Test transcription")
    
    # Test successful email sending
    mock_smtp_instance = mock.Mock()
    mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
    
    result = send_email_alert(test_audio_file, transcription_file)
    
    assert result is True
    mock_smtp.assert_called_once_with("localhost", 587)
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("test", "test")
    mock_smtp_instance.send_message.assert_called_once()


@mock.patch("transcribe.batch.smtplib.SMTP")
def test_send_email_alert_failure(mock_smtp, test_audio_file, temp_dir, mock_env_vars):
    """Test handling of email sending failures."""
    # Create mock transcription file
    transcription_file = temp_dir / "test_transcription.md"
    transcription_file.write_text("Test transcription")
    
    # Test failure due to SMTP exception
    mock_smtp.return_value.__enter__.side_effect = Exception("SMTP error")
    
    result = send_email_alert(test_audio_file, transcription_file)
    
    assert result is False


def test_send_email_alert_invalid_config(test_audio_file, temp_dir):
    """Test handling email alert with invalid configuration."""
    # Create mock transcription file
    transcription_file = temp_dir / "test_transcription.md"
    transcription_file.write_text("Test transcription")
    
    # Clear environment variables
    with mock.patch.dict(os.environ, clear=True):
        result = send_email_alert(test_audio_file, transcription_file)
        assert result is False


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
    
    # Check that the transcribed file is not included
    for file_path, _ in new_files:
        assert file_path.name != "test_audio_0.mp3"


def test_find_new_media_files_nonexistent_dir():
    """Test finding new media files in a non-existent directory."""
    result = find_new_media_files("/nonexistent/directory")
    assert result == []


def test_process_folder(temp_batch_dir, mock_env_vars):
    """Test processing a folder of media files."""
    # Mock the transcription function to avoid actual API calls
    with mock.patch("transcribe.batch.transcribe_audio_file") as mock_transcribe:
        # Set up the mock to create actual output files
        def side_effect(path):
            output_path = Path(path).with_name(f"{Path(path).stem}_transcription.md")
            output_path.write_text("Mock transcription")
            return output_path
        mock_transcribe.side_effect = side_effect
        
        # Process the folder
        result = process_folder(str(temp_batch_dir))
        
        # Should be successful
        assert result is True
        
        # Should have called transcribe_audio_file 3 times
        assert mock_transcribe.call_count == 3
        
        # Check that transcription files were created
        for i in range(3):
            transcription_file = temp_batch_dir / f"test_audio_{i}_transcription.md"
            assert transcription_file.exists()


def test_process_folder_with_email(temp_batch_dir, mock_env_vars):
    """Test processing a folder with email notifications."""
    # Mock the transcription function and email function
    with mock.patch("transcribe.batch.transcribe_audio_file") as mock_transcribe:
        with mock.patch("transcribe.batch.send_email_alert") as mock_email:
            # Set up the transcription mock
            def side_effect(path):
                output_path = Path(path).with_name(f"{Path(path).stem}_transcription.md")
                output_path.write_text("Mock transcription")
                return output_path
            mock_transcribe.side_effect = side_effect
            
            # Set up the email mock
            mock_email.return_value = True
            
            # Process the folder with email notifications
            result = process_folder(str(temp_batch_dir), send_emails=True)
            
            # Should be successful
            assert result is True
            
            # Should have called transcribe_audio_file 3 times
            assert mock_transcribe.call_count == 3
            
            # Should have called send_email_alert 3 times
            assert mock_email.call_count == 3


def test_process_folder_some_failures(temp_batch_dir, mock_env_vars):
    """Test processing a folder with some transcription failures."""
    # Mock the transcription function to fail for some files
    with mock.patch("transcribe.batch.transcribe_audio_file") as mock_transcribe:
        # Set up the mock to succeed for even indices and fail for odd indices
        def side_effect(path):
            file_path = Path(path)
            if "1" in file_path.name:  # Fail for test_audio_1.mp3
                return None
            output_path = file_path.with_name(f"{file_path.stem}_transcription.md")
            output_path.write_text("Mock transcription")
            return output_path
        mock_transcribe.side_effect = side_effect
        
        # Process the folder
        result = process_folder(str(temp_batch_dir))
        
        # Should not be fully successful
        assert result is False
        
        # Check that only some transcription files were created
        assert (temp_batch_dir / "test_audio_0_transcription.md").exists()
        assert not (temp_batch_dir / "test_audio_1_transcription.md").exists()
        assert (temp_batch_dir / "test_audio_2_transcription.md").exists()


def test_process_empty_folder(temp_dir):
    """Test processing an empty folder."""
    result = process_folder(str(temp_dir))
    
    # Should be successful (no files to process)
    assert result is True 