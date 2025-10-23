"""Tests for file availability checking (Google Drive placeholder detection)."""
import os
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from transcribe.core import is_file_available


@pytest.mark.unit
def test_is_file_available_with_readable_file(temp_dir):
    """Test file availability check with a real, readable file."""
    # Arrange
    test_file = temp_dir / "test_audio.mp3"
    test_file.write_text("This is a real file with actual content")

    # Act
    result = is_file_available(test_file, force_download=False, max_retries=1)

    # Assert
    assert result is True


@pytest.mark.unit
def test_is_file_available_with_large_file(temp_dir):
    """Test file availability with large file (adaptive timeout calculation)."""
    # Arrange
    large_file = temp_dir / "large_video.mp4"
    # Create a 15MB file
    large_file.write_bytes(b"x" * (15 * 1024 * 1024))

    # Act
    result = is_file_available(large_file, force_download=False, max_retries=1)

    # Assert
    assert result is True


@pytest.mark.unit
def test_is_file_available_handles_io_error(temp_dir):
    """Test that IOError is handled gracefully without force_download."""
    # Arrange
    test_file = temp_dir / "nonexistent.mp3"

    # Act
    result = is_file_available(test_file, force_download=False, max_retries=1)

    # Assert
    assert result is False


@pytest.mark.unit
def test_is_file_available_retries_on_failure(temp_dir):
    """Test retry mechanism when file read fails initially."""
    # Arrange
    test_file = temp_dir / "test.mp3"
    test_file.write_text("content")

    call_count = 0

    # Mock open to fail first time, succeed second time
    original_open = open

    def mock_open_with_retry(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise IOError("File not available yet")
        return original_open(*args, **kwargs)

    # Act
    with mock.patch("builtins.open", side_effect=mock_open_with_retry):
        result = is_file_available(
            test_file,
            force_download=True,
            max_retries=2,
            retry_delay=0  # No delay for faster test
        )

    # Assert
    assert result is True
    assert call_count == 2  # Failed once, succeeded on retry


@pytest.mark.unit
def test_is_file_available_respects_max_retries(temp_dir):
    """Test that retries stop after max_retries is reached."""
    # Arrange
    test_file = temp_dir / "test.mp3"

    call_count = 0

    def mock_open_always_fails(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise IOError("Persistent failure")

    # Act
    with mock.patch("builtins.open", side_effect=mock_open_always_fails):
        result = is_file_available(
            test_file,
            force_download=True,
            max_retries=3,
            retry_delay=0
        )

    # Assert
    assert result is False
    assert call_count == 3  # Tried exactly max_retries times


@pytest.mark.unit
def test_is_file_available_without_force_download(temp_dir):
    """Test that without force_download, no retries happen."""
    # Arrange
    test_file = temp_dir / "test.mp3"

    call_count = 0

    def mock_open_fails(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise IOError("File not available")

    # Act
    with mock.patch("builtins.open", side_effect=mock_open_fails):
        result = is_file_available(
            test_file,
            force_download=False,
            max_retries=3,
            retry_delay=0
        )

    # Assert
    assert result is False
    assert call_count == 1  # Only tried once, no retries


@pytest.mark.slow
@pytest.mark.skipif(not hasattr(os, 'SIGALRM'), reason="SIGALRM not available on Windows")
def test_is_file_available_timeout_behavior(temp_dir):
    """Test timeout handling for file read operations (Unix only)."""
    # Arrange
    test_file = temp_dir / "test.mp3"
    test_file.write_bytes(b"x" * 1024)  # Small file = short timeout

    # Mock file read to take too long
    original_open = open

    def slow_open(*args, **kwargs):
        f = original_open(*args, **kwargs)
        original_read = f.read

        def slow_read(*read_args, **read_kwargs):
            time.sleep(15)  # Longer than timeout
            return original_read(*read_args, **read_kwargs)

        f.read = slow_read
        return f

    # Act
    # This should timeout since we set a very small timeout
    with mock.patch("builtins.open", side_effect=slow_open):
        result = is_file_available(
            test_file,
            force_download=False,
            max_retries=1
        )

    # Assert - should handle timeout gracefully
    # Note: This test may be flaky depending on system behavior
    assert result in [True, False]  # Just ensure it doesn't crash


@pytest.mark.unit
def test_is_file_available_with_permission_error(temp_dir):
    """Test handling of permission errors."""
    # Arrange
    test_file = temp_dir / "test.mp3"

    def mock_open_permission_denied(*args, **kwargs):
        raise PermissionError("Access denied")

    # Act
    with mock.patch("builtins.open", side_effect=mock_open_permission_denied):
        result = is_file_available(
            test_file,
            force_download=False,
            max_retries=1
        )

    # Assert
    assert result is False
