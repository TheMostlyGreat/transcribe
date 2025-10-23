"""Tests for handling file paths and filenames with spaces."""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from transcribe.core import transcribe_audio_file_original, is_supported_file
from .mocks import MockAssemblyAI, MockTranscriptResponse


@pytest.mark.unit
def test_is_supported_file_with_spaces():
    """Test file extension detection with spaces in filename."""
    # Arrange
    files_with_spaces = [
        Path("my audio file.mp3"),
        Path("interview with John Doe.wav"),
        Path("conference call 2025.mp4"),
        Path("output dir with spaces/recording.m4a"),
    ]

    # Act & Assert
    for file_path in files_with_spaces:
        assert is_supported_file(file_path) is True


@pytest.mark.unit
def test_output_path_generation_with_spaces(temp_dir):
    """Test that output paths are correctly generated for files with spaces."""
    # Arrange
    input_file = temp_dir / "my audio file.mp3"
    input_file.write_text("fake audio data")
    expected_output = temp_dir / "my audio file_transcription.md"

    mock_response = MockTranscriptResponse()
    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = mock_response
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)

    # Act
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(str(input_file))

    # Assert
    assert output_path is not None
    assert output_path == expected_output
    assert output_path.exists()


@pytest.mark.unit
def test_custom_output_path_with_spaces(temp_dir):
    """Test custom output path with spaces in directory and filename."""
    # Arrange
    input_file = temp_dir / "input.mp3"
    input_file.write_text("fake audio data")

    output_dir = temp_dir / "output dir with spaces"
    output_dir.mkdir()
    custom_output = output_dir / "my transcription file.md"

    mock_response = MockTranscriptResponse()
    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = mock_response
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)

    # Act
    with mock.patch("transcribe.core.aai", mock_aai):
        output_path = transcribe_audio_file_original(
            str(input_file),
            output_path=str(custom_output)
        )

    # Assert
    assert output_path is not None
    assert output_path == custom_output
    assert output_path.exists()
    assert output_path.parent == output_dir


@pytest.mark.integration
def test_batch_processing_with_spaces(temp_dir, mock_env_vars):
    """Test batch processing with directory and filenames containing spaces."""
    # Arrange
    batch_dir = temp_dir / "media files with spaces"
    batch_dir.mkdir()

    # Create test files with spaces in names
    test_files = [
        "interview with CEO.mp3",
        "team meeting notes.wav",
        "conference call 2025-01-15.m4a"
    ]

    for filename in test_files:
        file_path = batch_dir / filename
        file_path.write_text("fake audio data")

    # Mock transcription
    def mock_transcribe(path, output_path=None, retry_existing=False):
        file_path = Path(path)
        if output_path is None:
            output_path = file_path.with_name(f"{file_path.stem}_transcription.md")
        else:
            output_path = Path(output_path)
        output_path.write_text("Mock transcription")
        return output_path

    # Act
    from transcribe.batch import process_folder
    with mock.patch("transcribe.batch.transcribe_audio_file", side_effect=mock_transcribe):
        success, count = process_folder(str(batch_dir))

    # Assert
    assert success is True
    assert count == 3

    # Verify output files were created with correct names
    expected_outputs = [
        "interview with CEO_transcription.md",
        "team meeting notes_transcription.md",
        "conference call 2025-01-15_transcription.md"
    ]

    for output_name in expected_outputs:
        output_file = batch_dir / output_name
        assert output_file.exists(), f"Expected output file not found: {output_name}"


@pytest.mark.unit
def test_path_object_handling_preserves_spaces(temp_dir):
    """Test that Path objects correctly preserve spaces throughout processing."""
    # Arrange
    filename_with_spaces = "my test file.mp3"
    file_path = temp_dir / filename_with_spaces
    file_path.write_text("fake audio")

    # Act
    path_obj = Path(str(file_path))
    output_path = path_obj.with_name(f"{path_obj.stem}_transcription.md")

    # Assert
    assert " " in str(output_path)
    assert output_path.name == "my test file_transcription.md"
    assert output_path.parent == temp_dir
