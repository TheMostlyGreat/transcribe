"""
Test fixtures and configuration for pytest.
"""
import os
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def test_files_dir():
    """Return the path to the test files directory."""
    return Path(__file__).parent / "test_files"


@pytest.fixture
def test_audio_file(test_files_dir):
    """Return the path to a test audio file."""
    return test_files_dir / "test_audio.mp3"


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Clean up
    shutil.rmtree(temp_path)


@pytest.fixture
def temp_batch_dir(temp_dir, test_audio_file):
    """Create a temporary directory with multiple audio files for batch testing."""
    # Create files
    for i in range(3):
        output_file = temp_dir / f"test_audio_{i}.mp3"
        shutil.copy(test_audio_file, output_file)
    
    yield temp_dir


@pytest.fixture
def mock_env_vars():
    """Mock environment variables required for testing."""
    # Save original environment
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["ASSEMBLY_API_KEY"] = "test_api_key"
    os.environ["SMTP_SERVER"] = "localhost"
    os.environ["SMTP_PORT"] = "587"
    os.environ["SMTP_USERNAME"] = "test"
    os.environ["SMTP_PASSWORD"] = "test"
    os.environ["EMAIL_FROM"] = "from@example.com"
    os.environ["EMAIL_TO"] = "to@example.com"
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env) 