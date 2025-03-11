"""Tests for the core transcription functionality."""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# Add parent directory to sys.path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from transcribe.core import (
    get_api_key, 
    setup_client, 
    is_supported_file, 
    get_media_type, 
    transcribe_audio_file_original
)
# Use a relative import for mocks
from .mocks import MockAssemblyAI, MockUtterance, MockTranscriptResponse, create_error_response


def test_get_api_key(mock_env_vars):
    """Test retrieving API key from environment."""
    assert get_api_key() == "test_api_key"
    
    # Test missing API key
    with mock.patch.dict(os.environ, {"ASSEMBLY_API_KEY": ""}):
        assert get_api_key() is None


def test_setup_client(mock_env_vars):
    """Test client setup with API key."""
    with mock.patch("transcribe.core.aai", MockAssemblyAI()):
        assert setup_client() is True
        
    # Test with missing API key
    with mock.patch.dict(os.environ, clear=True):
        with mock.patch("transcribe.core.aai", MockAssemblyAI()):
            assert setup_client() is False


def test_is_supported_file():
    """Test supported file extension detection."""
    # Test supported extensions
    assert is_supported_file(Path("test.mp3")) is True
    assert is_supported_file(Path("test.wav")) is True
    assert is_supported_file(Path("test.mp4")) is True
    assert is_supported_file(Path("test.MOV")) is True  # Test case insensitivity
    
    # Test unsupported extensions
    assert is_supported_file(Path("test.txt")) is False
    assert is_supported_file(Path("test.pdf")) is False


def test_get_media_type():
    """Test media type detection."""
    # Test audio files
    assert get_media_type(Path("test.mp3")) == "audio"
    assert get_media_type(Path("test.wav")) == "audio"
    
    # Test video files
    assert get_media_type(Path("test.mp4")) == "video"
    assert get_media_type(Path("test.mov")) == "video"


def test_transcribe_audio_file_scenarios(test_audio_file, temp_dir, mock_env_vars):
    """Test various transcription scenarios."""
    # Setup for successful transcription with speaker labels
    utterances = [
        MockUtterance(speaker="A", text="This is speaker A.", start=0, end=2000),
        MockUtterance(speaker="B", text="This is speaker B.", start=2500, end=4500)
    ]
    mock_response = MockTranscriptResponse(utterances=utterances)
    
    # 1. Test successful transcription with speaker labels
    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = mock_response
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)
    
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(temp_dir / "output.md")
        )
        
        assert output_path is not None
        assert output_path.exists()
        
        content = output_path.read_text()
        assert "# Transcription of" in content
        assert "**Speaker A:**" in content
        assert "**Speaker B:**" in content
    
    # 2. Test successful transcription without speaker labels
    mock_response_no_speakers = MockTranscriptResponse(utterances=[])
    mock_transcriber.transcribe.return_value = mock_response_no_speakers
    
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(temp_dir / "output_no_speakers.md")
        )
        
        assert output_path is not None
        assert output_path.exists()
        
        content = output_path.read_text()
        assert "# Transcription of" in content
        assert "**Speaker" not in content
    
    # 3. Test error handling
    mock_transcriber.transcribe.return_value = create_error_response()
    
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(temp_dir / "output_error.md")
        )
        
        assert output_path is None
    
    # 4. Test non-existent file
    nonexistent_file = temp_dir / "nonexistent.mp3"
    
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(str(nonexistent_file))
        assert output_path is None
    
    # 5. Test unsupported file format
    unsupported_file = temp_dir / "test.txt"
    unsupported_file.write_text("This is not an audio file")
    
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(str(unsupported_file))
        assert output_path is None 