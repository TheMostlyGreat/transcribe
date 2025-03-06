"""
Tests for the core transcription functionality.
"""
import os
from pathlib import Path
from unittest import mock

import pytest

from transcribe.core import (
    get_api_key, 
    setup_client, 
    is_supported_file, 
    get_media_type, 
    transcribe_audio_file_original
)
from tests.mocks import MockAssemblyAI, MockTranscriptResponse, create_error_response


def test_get_api_key(mock_env_vars):
    """Test retrieving API key from environment."""
    assert get_api_key() == "test_api_key"
    
    # Test missing API key
    with mock.patch.dict(os.environ, {"ASSEMBLY_API_KEY": ""}):
        assert get_api_key() is None
        
    with mock.patch.dict(os.environ, clear=True):
        assert get_api_key() is None


def test_setup_client(mock_env_vars):
    """Test client setup with API key."""
    # Mock the assemblyai module
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
    assert is_supported_file(Path("test")) is False


def test_get_media_type():
    """Test media type detection."""
    # Test audio files
    assert get_media_type(Path("test.mp3")) == "audio"
    assert get_media_type(Path("test.wav")) == "audio"
    assert get_media_type(Path("test.flac")) == "audio"
    
    # Test video files
    assert get_media_type(Path("test.mp4")) == "video"
    assert get_media_type(Path("test.mov")) == "video"
    assert get_media_type(Path("test.avi")) == "video"


def test_transcribe_audio_file_with_speaker_labels(test_audio_file, temp_dir, mock_env_vars):
    """Test transcribing an audio file with speaker labels."""
    # Mock the assemblyai module
    with mock.patch("transcribe.core.aai", MockAssemblyAI()):
        output_path = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(temp_dir / "output.md")
        )
        
        assert output_path is not None
        assert output_path.exists()
        
        # Check content of the output file
        content = output_path.read_text()
        assert "# Transcription of" in content
        assert "**Speaker A:** This is speaker A." in content
        assert "**Speaker B:** This is speaker B." in content


def test_transcribe_audio_file_without_speaker_labels(test_audio_file, temp_dir, mock_env_vars):
    """Test transcribing an audio file without speaker labels."""
    # Create a mock response without utterances
    mock_response = MockTranscriptResponse(utterances=[])
    
    # Mock the transcriber to return our custom response
    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = mock_response
    
    # Mock the assemblyai module and its Transcriber class
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)
    
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(temp_dir / "output_no_speakers.md")
        )
        
        assert output_path is not None
        assert output_path.exists()
        
        # Check content of the output file
        content = output_path.read_text()
        assert "# Transcription of" in content
        assert "This is a mock transcription for testing." in content
        # No speaker labels
        assert "**Speaker" not in content


def test_transcribe_audio_file_error(test_audio_file, temp_dir, mock_env_vars):
    """Test handling of transcription errors."""
    # Mock the transcriber to return an error response
    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = create_error_response()
    
    # Mock the assemblyai module and its Transcriber class
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)
    
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(temp_dir / "output_error.md")
        )
        
        # Should return None on error
        assert output_path is None


def test_transcribe_audio_file_nonexistent_file(temp_dir, mock_env_vars):
    """Test transcribing a non-existent file."""
    nonexistent_file = temp_dir / "nonexistent.mp3"
    
    with mock.patch("transcribe.core.aai", MockAssemblyAI()):
        output_path = transcribe_audio_file_original(str(nonexistent_file))
        assert output_path is None


def test_transcribe_audio_file_unsupported_format(temp_dir, mock_env_vars):
    """Test transcribing a file with unsupported format."""
    # Create a text file with .txt extension
    unsupported_file = temp_dir / "test.txt"
    unsupported_file.write_text("This is not an audio file")
    
    with mock.patch("transcribe.core.aai", MockAssemblyAI()):
        output_path = transcribe_audio_file_original(str(unsupported_file))
        assert output_path is None


@pytest.mark.skip(reason="AssemblyAI package is installed, so we can't test the mock")
def test_mock_aai_module():
    """Test the mock AAI module created for testing."""
    # This test is simpler - we'll just check that the mock is created
    from transcribe.core import aai
    
    # Check that the mock has the expected attributes
    assert hasattr(aai, 'Settings')
    assert hasattr(aai, 'Transcriber')
    assert hasattr(aai, 'TranscriptionConfig')
    
    # Test the mock Transcriber
    transcriber = aai.Transcriber()
    
    # The mock transcriber should have a transcribe method
    assert hasattr(transcriber, 'transcribe')


def test_transcribe_audio_file_original_with_error(test_audio_file, temp_dir):
    """Test the original transcribe_audio_file function with an error."""
    # Import the module
    from transcribe import core
    
    # Mock the setup_client function to return True
    with mock.patch('transcribe.core.setup_client', return_value=True):
        # Mock the aai.Transcriber.transcribe method to return an error
        mock_response = mock.Mock()
        mock_response.error = "Test error"
        mock_transcriber = mock.Mock()
        mock_transcriber.transcribe.return_value = mock_response
        
        with mock.patch('transcribe.core.aai.Transcriber', return_value=mock_transcriber):
            # Call the function
            result = core.transcribe_audio_file_original(
                str(test_audio_file),
                output_path=str(temp_dir / "error_output.md")
            )
            
            # Should return None due to the error
            assert result is None


def test_transcribe_audio_file_original_no_text(test_audio_file, temp_dir):
    """Test the original transcribe_audio_file function with no text in response."""
    # Import the module
    from transcribe import core
    
    # Mock the setup_client function to return True
    with mock.patch('transcribe.core.setup_client', return_value=True):
        # Mock the aai.Transcriber.transcribe method to return a response with no text
        mock_response = mock.Mock()
        mock_response.error = None
        mock_response.text = ""
        mock_response.status = "processing"
        mock_transcriber = mock.Mock()
        mock_transcriber.transcribe.return_value = mock_response
        
        with mock.patch('transcribe.core.aai.Transcriber', return_value=mock_transcriber):
            # Call the function
            result = core.transcribe_audio_file_original(
                str(test_audio_file),
                output_path=str(temp_dir / "no_text_output.md")
            )
            
            # Should return None due to no text
            assert result is None


def test_transcribe_audio_file_original_no_utterances(test_audio_file, temp_dir):
    """Test the original transcribe_audio_file function with no utterances."""
    # Import the module
    from transcribe import core
    
    # Mock the setup_client function to return True
    with mock.patch('transcribe.core.setup_client', return_value=True):
        # Mock the aai.Transcriber.transcribe method to return a response with no utterances
        mock_response = mock.Mock()
        mock_response.error = None
        mock_response.text = "Test transcription without utterances"
        mock_response.status = "completed"
        mock_response.utterances = []
        mock_transcriber = mock.Mock()
        mock_transcriber.transcribe.return_value = mock_response
        
        with mock.patch('transcribe.core.aai.Transcriber', return_value=mock_transcriber):
            # Call the function
            result = core.transcribe_audio_file_original(
                str(test_audio_file),
                output_path=str(temp_dir / "no_utterances_output.md")
            )
            
            # Should return a Path object
            assert result is not None
            assert isinstance(result, Path)
            assert result.exists()
            
            # Check the content
            content = result.read_text()
            assert "Test transcription without utterances" in content 