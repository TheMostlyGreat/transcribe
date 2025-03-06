"""
Integration tests for the transcribe package.
"""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

from transcribe.cli import cli_main
from transcribe.core import transcribe_audio_file, mock_transcribe_for_testing


@pytest.fixture
def setup_mock_transcribe():
    """Set up mock transcription for testing."""
    # Save the original function
    original_function = transcribe_audio_file
    
    # Use the mock function for testing
    yield
    
    # Restore the original function after the test
    globals()['transcribe_audio_file'] = original_function


def test_main_file_command(test_audio_file, temp_dir, setup_mock_transcribe, mock_env_vars):
    """Test the main function with file command."""
    # Mock the command-line arguments
    output_path = temp_dir / "output.md"
    test_args = ['file', str(test_audio_file), '--output', str(output_path)]
    
    # Run the CLI main function directly instead of the package main
    result = cli_main(test_args)
    
    # Should return success code
    assert result == 0
    
    # Output file should exist
    assert output_path.exists()


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


@mock.patch('transcribe.core.aai')
def test_real_transcription_flow(mock_aai, test_audio_file, temp_dir, mock_env_vars):
    """Test the real transcription flow with mocked AssemblyAI."""
    # Set up the mock transcriber
    mock_transcriber = mock.Mock()
    mock_response = mock.Mock()
    mock_response.id = "test-id"
    mock_response.status = "completed"
    mock_response.text = "Test transcription"
    mock_response.error = None  # Explicitly set error to None
    mock_utterance1 = mock.Mock()
    mock_utterance1.speaker = "A"
    mock_utterance1.text = "Test speaker A"
    mock_utterance2 = mock.Mock()
    mock_utterance2.speaker = "B"
    mock_utterance2.text = "Test speaker B"
    mock_response.utterances = [mock_utterance1, mock_utterance2]
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