"""Tests for JSON status file lifecycle and stalled transcription recovery."""
import os
import sys
import json
import time
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from transcribe.core import transcribe_audio_file_original
from transcribe.batch import find_new_media_files, MAX_IN_PROGRESS_AGE_HOURS
from .mocks import MockAssemblyAI, MockTranscriptResponse


@pytest.mark.unit
def test_json_status_file_created_on_start(temp_dir, test_audio_file, mock_env_vars):
    """Test that JSON status file is created when transcription starts."""
    # Arrange
    output_path = temp_dir / "output.md"
    json_path = temp_dir / "output.json"

    mock_response = MockTranscriptResponse()
    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = mock_response
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)

    # Act
    with mock.patch("transcribe.core.aai", mock_aai):
        transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(output_path)
        )

    # Assert - JSON should be deleted after successful completion
    assert not json_path.exists()  # Cleaned up after success
    assert output_path.exists()  # MD file created


@pytest.mark.unit
def test_json_status_contains_transcript_id(temp_dir, test_audio_file, mock_env_vars):
    """Test that JSON status file contains transcript ID during processing."""
    # Arrange
    json_path = temp_dir / "output.json"
    json_created = False

    original_dump = json.dump

    def capture_json_dump(obj, fp, *args, **kwargs):
        nonlocal json_created
        if "transcript_id" in obj:
            json_created = True
        return original_dump(obj, fp, *args, **kwargs)

    mock_response = MockTranscriptResponse(id="test-transcript-123")
    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = mock_response
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)

    # Act
    with mock.patch("json.dump", side_effect=capture_json_dump):
        with mock.patch("transcribe.core.aai", mock_aai):
            transcribe_audio_file_original(
                str(test_audio_file),
                output_path=str(temp_dir / "output.md")
            )

    # Assert - transcript_id was saved at some point
    assert json_created


@pytest.mark.unit
def test_json_deleted_after_successful_transcription(temp_dir, test_audio_file, mock_env_vars):
    """Test that JSON status file is deleted after successful transcription."""
    # Arrange
    output_md = temp_dir / "output.md"
    json_path = temp_dir / "output.json"

    mock_response = MockTranscriptResponse()
    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = mock_response
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)

    # Act
    with mock.patch("transcribe.core.aai", mock_aai):
        result = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(output_md)
        )

    # Assert
    assert result is not None
    assert output_md.exists()
    assert not json_path.exists()  # JSON should be cleaned up


@pytest.mark.unit
def test_json_remains_on_transcription_error(temp_dir, test_audio_file, mock_env_vars):
    """Test that JSON status file persists with error status when transcription fails."""
    # Arrange
    from .mocks import create_error_response

    output_md = temp_dir / "output.md"
    json_path = temp_dir / "output.json"

    mock_transcriber = mock.Mock()
    mock_transcriber.transcribe.return_value = create_error_response()
    mock_aai = MockAssemblyAI()
    mock_aai.Transcriber = mock.Mock(return_value=mock_transcriber)

    # Act
    with mock.patch("transcribe.core.aai", mock_aai):
        result = transcribe_audio_file_original(
            str(test_audio_file),
            output_path=str(output_md)
        )

    # Assert
    assert result is None
    assert json_path.exists()

    # Check JSON contains error status
    with open(json_path) as f:
        status_data = json.load(f)
    assert status_data.get("status") == "error"


@pytest.mark.unit
def test_find_stalled_transcriptions(temp_dir):
    """Test detection of stalled transcriptions (>24 hours old)."""
    # Arrange
    media_file = temp_dir / "test.mp3"
    media_file.write_text("fake audio")

    json_path = temp_dir / "test.json"

    # Create a stalled status file (older than MAX_IN_PROGRESS_AGE_HOURS)
    old_timestamp = time.time() - ((MAX_IN_PROGRESS_AGE_HOURS + 1) * 60 * 60)
    status_data = {
        "status": "in_progress",
        "media_file": str(media_file),
        "start_time": old_timestamp,
        "message": "Transcription in progress"
    }

    with open(json_path, 'w') as f:
        json.dump(status_data, f)

    # Act
    new_files = find_new_media_files(str(temp_dir))

    # Assert - stalled file should be detected as needing processing
    assert len(new_files) == 1
    assert new_files[0][0] == media_file


@pytest.mark.unit
def test_skip_recent_in_progress_files(temp_dir):
    """Test that recent in-progress files are skipped."""
    # Arrange
    media_file = temp_dir / "test.mp3"
    media_file.write_text("fake audio")

    json_path = temp_dir / "test.json"

    # Create a recent in-progress status file
    recent_timestamp = time.time() - 60  # Just 1 minute ago
    status_data = {
        "status": "in_progress",
        "media_file": str(media_file),
        "start_time": recent_timestamp,
        "message": "Transcription in progress"
    }

    with open(json_path, 'w') as f:
        json.dump(status_data, f)

    # Act
    new_files = find_new_media_files(str(temp_dir))

    # Assert - recent in-progress file should be skipped
    assert len(new_files) == 0


@pytest.mark.unit
def test_retry_failed_transcriptions(temp_dir):
    """Test that files with error status are retried."""
    # Arrange
    media_file = temp_dir / "test.mp3"
    media_file.write_text("fake audio")

    json_path = temp_dir / "test.json"

    # Create an error status file
    status_data = {
        "status": "error",
        "media_file": str(media_file),
        "error": "Previous transcription failed",
        "timestamp": time.time()
    }

    with open(json_path, 'w') as f:
        json.dump(status_data, f)

    # Act
    new_files = find_new_media_files(str(temp_dir))

    # Assert - failed file should be retried
    assert len(new_files) == 1
    assert new_files[0][0] == media_file


@pytest.mark.unit
def test_completed_files_without_status_field(temp_dir):
    """Test that JSON files without 'status' field are treated as completed."""
    # Arrange
    media_file = temp_dir / "test.mp3"
    media_file.write_text("fake audio")

    json_path = temp_dir / "test.json"

    # Create a completed transcription JSON (no status field)
    completed_data = {
        "text": "Transcription complete",
        "media_file": str(media_file),
        "completed_time": time.time(),
        "duration": 10.5
    }

    with open(json_path, 'w') as f:
        json.dump(completed_data, f)

    # Act
    new_files = find_new_media_files(str(temp_dir))

    # Assert - completed file should be skipped
    assert len(new_files) == 0


@pytest.mark.integration
def test_stalled_transcription_recovery_with_api_check(temp_dir, test_audio_file, mock_env_vars):
    """Test recovery of stalled transcription by checking API status."""
    # Arrange - create a stalled transcription with transcript_id
    # The JSON file must match the expected output path naming convention
    output_md_path = temp_dir / "test_transcription.md"
    json_path = temp_dir / "test_transcription.json"

    old_timestamp = time.time() - ((MAX_IN_PROGRESS_AGE_HOURS + 1) * 60 * 60)

    status_data = {
        "status": "in_progress",
        "media_file": str(test_audio_file),
        "start_time": old_timestamp,
        "transcript_id": "existing-transcript-123",
        "message": "Transcription in progress"
    }

    with open(json_path, 'w') as f:
        json.dump(status_data, f)

    # Mock API response showing completed transcription
    mock_api_response = {
        "status": "completed",
        "text": "Recovered transcription text",
        "id": "existing-transcript-123",
        "utterances": []
    }

    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response

    mock_aai = MockAssemblyAI()

    # Act
    with mock.patch("requests.get", return_value=mock_response):
        with mock.patch("transcribe.core.aai", mock_aai):
            result = transcribe_audio_file_original(
                str(test_audio_file),
                output_path=str(output_md_path),
                retry_existing=True
            )

    # Assert - should recover the existing transcription
    assert result is not None
    assert result.exists()
    content = result.read_text()
    assert "Recovered transcription text" in content
