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


@pytest.mark.unit
def test_transcribe_with_speaker_labels(test_audio_file, temp_dir, mock_env_vars):
    """Test successful transcription with speaker diarization."""
    # Arrange
    utterances = [
        MockUtterance(speaker="A", text="This is speaker A.", start=0, end=2000),
        MockUtterance(speaker="B", text="This is speaker B.", start=2500, end=4500)
    ]
    mock_response = MockTranscriptResponse(utterances=utterances)

    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = mock_response
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)

    # Act
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(temp_dir / "output.md")
        )

    # Assert
    assert output_path is not None
    assert output_path.exists()

    content = output_path.read_text()
    assert "# Transcription of" in content
    assert "**Speaker A:**" in content
    assert "**Speaker B:**" in content


@pytest.mark.unit
def test_transcribe_without_speaker_labels(test_audio_file, temp_dir, mock_env_vars):
    """Test successful transcription without speaker diarization."""
    # Arrange
    mock_response = MockTranscriptResponse(utterances=[])

    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = mock_response
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)

    # Act
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(temp_dir / "output_no_speakers.md")
        )

    # Assert
    assert output_path is not None
    assert output_path.exists()

    content = output_path.read_text()
    assert "# Transcription of" in content
    assert "**Speaker" not in content


@pytest.mark.unit
def test_transcribe_handles_api_error(test_audio_file, temp_dir, mock_env_vars):
    """Test that API errors are handled gracefully."""
    # Arrange
    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = create_error_response()
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)

    # Act
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(temp_dir / "output_error.md")
        )

    # Assert
    assert output_path is None


@pytest.mark.unit
def test_transcribe_rejects_missing_file(temp_dir, mock_env_vars):
    """Test that missing files are rejected with clear error."""
    # Arrange
    nonexistent_file = temp_dir / "nonexistent.mp3"
    mock_aai = MockAssemblyAI()

    # Act
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(str(nonexistent_file))

    # Assert
    assert output_path is None


@pytest.mark.unit
def test_transcribe_rejects_unsupported_format(temp_dir, mock_env_vars):
    """Test that unsupported file formats are rejected."""
    # Arrange
    unsupported_file = temp_dir / "test.txt"
    unsupported_file.write_text("This is not an audio file")
    mock_aai = MockAssemblyAI()

    # Act
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(str(unsupported_file))

    # Assert
    assert output_path is None 