"""
Integration tests for the transcribe package.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Add parent directory to sys.path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from transcribe.cli import cli_main
from transcribe.core import transcribe_audio_file, mock_transcribe_for_testing


@pytest.fixture
def setup_mock_transcribe():
    """Fixture to set up mock transcription API in the core module."""
    # Define a mock function for transcribing that succeeds and creates output files
    def mock_transcribe_fn(media_file_path, output_path=None, **kwargs):
        # Determine output path
        if output_path is None:
            media_path = Path(media_file_path)
            output_path = media_path.with_name(f"{media_path.stem}_transcription.md")
        else:
            output_path = Path(output_path)
        
        # Write a dummy transcription file
        with open(output_path, 'w') as f:
            f.write(f"# Mock Transcription of {Path(media_file_path).name}\n\n")
            f.write("This is a mock transcription created for testing purposes.\n")
        
        return output_path
    
    # Mock setup_client to always return success
    def mock_setup_client():
        return True
    
    # Mock get_api_key to always return a fake key
    def mock_get_api_key():
        return "fake-api-key-for-testing"
    
    # Apply all the mocks
    from transcribe import core, batch, cli
    
    with mock.patch('transcribe.core.get_api_key', side_effect=mock_get_api_key):
        with mock.patch('transcribe.core.setup_client', side_effect=mock_setup_client):
            with mock.patch('transcribe.core.transcribe_audio_file', side_effect=mock_transcribe_fn):
                with mock.patch('transcribe.core.transcribe_audio_file_original', side_effect=mock_transcribe_fn):
                    with mock.patch('transcribe.batch.transcribe_audio_file', side_effect=mock_transcribe_fn):
                        yield


def test_main_file_command(test_audio_file, temp_dir, setup_mock_transcribe, mock_env_vars):
    """Test the main function with file command."""
    # Mock the command-line arguments
    output_path = temp_dir / "output.md"
    test_args = ['file', str(test_audio_file), '--output', str(output_path)]
    
    # Define a function that will actually create the output file
    def mock_transcribe_that_creates_file(audio_path, output_path=None, **kwargs):
        # Make sure we have the correct output path
        if output_path is None:
            output_path = Path(audio_path).with_suffix(".md")
        else:
            output_path = Path(output_path)
        
        # Actually create the file
        with open(output_path, 'w') as f:
            f.write(f"# Mock Transcription of {Path(audio_path).name}\n\n")
            f.write("This is a mock transcription created for testing purposes.\n")
        
        return output_path
    
    # Mock the transcription function to ensure it creates the file
    with mock.patch('transcribe.cli.transcribe_audio_file', side_effect=mock_transcribe_that_creates_file):
        # Run the CLI main function
        result = cli_main(test_args)
        
        # Should return success code
        assert result == 0
        
        # Output file should exist
        assert output_path.exists(), f"Output file {output_path} does not exist"
        
        # Check content of output file
        content = output_path.read_text()
        assert "Mock Transcription of" in content


def test_main_batch_command(temp_batch_dir, setup_mock_transcribe, mock_env_vars):
    """Test the main function with batch command."""
    # Mock the command-line arguments
    test_args = ['batch', str(temp_batch_dir)]
    
    # Run the CLI main function directly
    result = cli_main(test_args)
    
    # Should return success code
    assert result == 0
    
    # Output files should exist
    for i in range(3):
        output_path = temp_batch_dir / f"test_audio_{i}_transcription.md"
        assert output_path.exists()
        
        # Check content of output file
        content = output_path.read_text()
        assert "Mock Transcription of" in content


@mock.patch('transcribe.core.aai')
def test_real_transcription_flow(mock_aai, test_audio_file, temp_dir, mock_env_vars):
    """Test the real transcription flow with mocked AssemblyAI."""
    # Import our mock classes
    from tests.mocks import MockUtterance, MockTranscriptResponse
    
    # Set up the mock transcriber
    mock_transcriber = mock.Mock()
    
    # Create proper utterance objects instead of generic mocks
    utterances = [
        MockUtterance(speaker="A", text="Test speaker A", start=0, end=2000),
        MockUtterance(speaker="B", text="Test speaker B", start=2500, end=5000)
    ]
    
    # Create a response with our proper utterances
    mock_response = MockTranscriptResponse(
        id="test-id",
        status="completed",
        text="Test transcription",
        error=None,
        utterances=utterances
    )
    
    # Set up the mock transcriber to return our response
    mock_transcriber.transcribe.return_value = mock_response
    
    # Set up the mock aai module
    mock_aai.Transcriber.return_value = mock_transcriber
    mock_aai.TranscriptionConfig = mock.Mock(return_value=mock.Mock())
    
    # Run the transcription
    from transcribe.core import transcribe_audio_file_original
    output_path = transcribe_audio_file_original(
        str(test_audio_file),
        output_path=str(temp_dir / "real_output.md")
    )
    
    # Check the result
    assert output_path is not None
    assert output_path.exists()
    
    # Check the content
    content = output_path.read_text()
    assert "# Transcription of" in content
    assert "**Speaker A:** Test speaker A" in content
    assert "**Speaker B:** Test speaker B" in content 