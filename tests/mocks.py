"""
Mock objects for testing the transcribe package.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MockUtterance:
    """Mock for AssemblyAI utterance object."""
    speaker: str
    text: str


@dataclass
class MockTranscriptResponse:
    """Mock for AssemblyAI transcript response object."""
    id: str = "mock-transcript-12345"
    status: str = "completed"
    text: str = "This is a mock transcription for testing."
    error: Optional[str] = None
    utterances: Optional[List[MockUtterance]] = None
    
    def __post_init__(self):
        """Initialize default utterances if none provided."""
        if self.utterances is None:
            self.utterances = [
                MockUtterance(speaker="A", text="This is speaker A."),
                MockUtterance(speaker="B", text="This is speaker B."),
                MockUtterance(speaker="A", text="Speaker A again.")
            ]


class MockTranscriber:
    """Mock for AssemblyAI Transcriber class."""
    
    def transcribe(self, file_path, config=None):
        """Mock transcription method."""
        return MockTranscriptResponse()
    
    
# Mock AssemblyAI module for testing
class MockAssemblyAI:
    """Mock for the entire AssemblyAI module."""
    
    class TranscriptionConfig:
        """Mock TranscriptionConfig class."""
        def __init__(self, **kwargs):
            self.speaker_labels = kwargs.get('speaker_labels', True)
    
    class Transcriber:
        """Mock Transcriber class."""
        def transcribe(self, file_path, config=None):
            """Mock transcription method."""
            return MockTranscriptResponse()
    
    # Mock settings module
    class Settings:
        """Mock settings class."""
        api_key = None
    
    settings = Settings()


# Error response mock
def create_error_response():
    """Create a mock transcript response with an error."""
    return MockTranscriptResponse(
        status="error",
        text="",
        error="Mock transcription error",
        utterances=[]
    )


# No utterances response mock
def create_no_utterances_response():
    """Create a mock transcript response without utterances."""
    return MockTranscriptResponse(
        utterances=[]
    ) 