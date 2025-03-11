"""Root conftest.py for pytest configuration."""
import os
import sys
import tempfile
import pytest
from unittest import mock
from pathlib import Path

# Ensure version is available for all tests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcribe
if not hasattr(transcribe, '__version__'):
    transcribe.__version__ = "0.1"


@pytest.fixture
def test_audio_file():
    """Provide a temporary test audio file."""
    fd, filepath = tempfile.mkstemp(suffix='.mp3')
    os.write(fd, b'test audio data')
    os.close(fd)
    
    filepath = Path(filepath)
    yield filepath
    
    if filepath.exists():
        filepath.unlink()


@pytest.fixture
def mock_transcriber():
    """Mock the AssemblyAI transcriber with default responses."""
    with mock.patch('transcribe.core.setup_client', return_value=True):
        transcriber_mock = mock.MagicMock()
        
        # Setup default success response
        response_mock = mock.MagicMock()
        response_mock.status = "completed"
        response_mock.text = "Mocked transcription"
        response_mock.error = None
        
        # Add utterances for speaker diarization
        utterance1 = mock.MagicMock()
        utterance1.speaker = "A"
        utterance1.text = "Speaker A text"
        utterance1.start = 0
        utterance1.end = 5
        
        utterance2 = mock.MagicMock()
        utterance2.speaker = "B"
        utterance2.text = "Speaker B text"
        utterance2.start = 6
        utterance2.end = 10
        
        response_mock.utterances = [utterance1, utterance2]
        
        transcriber_mock.transcribe.return_value = response_mock
        
        with mock.patch('transcribe.core.aai.Transcriber', return_value=transcriber_mock):
            yield transcriber_mock 