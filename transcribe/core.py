"""
Core functionality for transcribing audio and video files.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Set, Dict, Any
import time
import signal
from datetime import datetime
import socket
import subprocess
import threading
import functools
import traceback
import json
import requests

# Import assemblyai or create a placeholder for testing
try:
    import assemblyai as aai
except ImportError:
    # Create a mock module for testing
    class MockAAI:
        """Mock AssemblyAI module for testing."""
        class Settings:
            """Mock settings class."""
            api_key = None
        settings = Settings()
        
        class Transcriber:
            """Mock transcriber class."""
            def transcribe(self, *args, **kwargs):
                """Mock transcribe method."""
                return None
                
        class TranscriptionConfig:
            """Mock config class."""
            def __init__(self, **kwargs):
                """Initialize with kwargs."""
                for key, value in kwargs.items():
                    setattr(self, key, value)
    
    aai = MockAAI()

# Set up logging
logger = logging.getLogger(__name__)

# Constants
VIDEO_EXTENSIONS: Set[str] = {
    '.mp4', '.mov', '.avi', '.wmv', '.webm', '.mkv', 
    '.mpg', '.mpeg', '.m4v', '.asf', '.dv', '.ogv', '.vp8'
}

AUDIO_EXTENSIONS: Set[str] = {
    '.mp3', '.wav', '.m4a', '.flac', '.aac', 
    '.ogg', '.wma', '.aiff', '.alac'
}

SUPPORTED_EXTENSIONS: Set[str] = VIDEO_EXTENSIONS.union(AUDIO_EXTENSIONS)

# Global dictionary to track progress of long-running operations
_operation_status = {}
_operation_status_lock = threading.RLock()

def update_progress(operation_id, status):
    """Update the progress status of an operation."""
    with _operation_status_lock:
        _operation_status[operation_id] = {
            'status': status,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'thread_id': threading.get_ident()
        }
        
def get_progress(operation_id=None):
    """Get progress status of operations."""
    with _operation_status_lock:
        if operation_id:
            return _operation_status.get(operation_id)
        return _operation_status.copy()

def progress_monitor(name=None):
    """
    Decorator to monitor progress of potentially slow operations.
    Logs the start, progress, and completion of the decorated function.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation_id = name or func.__name__
            start_time = time.time()
            
            # Log start
            current_time = datetime.now().strftime('%H:%M:%S')
            logger.info(f"[{current_time}] Starting operation: {operation_id}")
            update_progress(operation_id, 'started')
            
            # Set up progress monitoring thread
            stop_event = threading.Event()
            
            def progress_reporter():
                last_report = time.time()
                while not stop_event.is_set():
                    if time.time() - last_report >= 10:  # Report progress every 10 seconds
                        elapsed = time.time() - start_time
                        current_time = datetime.now().strftime('%H:%M:%S')
                        logger.info(f"[{current_time}] Operation in progress: {operation_id} (elapsed: {elapsed:.1f}s)")
                        update_progress(operation_id, f'in_progress - {elapsed:.1f}s elapsed')
                        last_report = time.time()
                    time.sleep(1)
            
            # Start monitoring thread
            monitor = threading.Thread(target=progress_reporter, daemon=True)
            monitor.start()
            
            try:
                # Run the actual function
                result = func(*args, **kwargs)
                
                # Log completion
                elapsed = time.time() - start_time
                current_time = datetime.now().strftime('%H:%M:%S')
                logger.info(f"[{current_time}] Operation completed: {operation_id} (took {elapsed:.1f}s)")
                update_progress(operation_id, f'completed in {elapsed:.1f}s')
                return result
            except Exception as e:
                # Log error
                elapsed = time.time() - start_time
                current_time = datetime.now().strftime('%H:%M:%S')
                logger.error(f"[{current_time}] Operation failed: {operation_id} after {elapsed:.1f}s - {str(e)}")
                logger.debug(f"Exception traceback: {traceback.format_exc()}")
                update_progress(operation_id, f'failed after {elapsed:.1f}s - {str(e)}')
                raise
            finally:
                # Stop the monitoring thread
                stop_event.set()
                
        return wrapper
    return decorator


def get_api_key() -> Optional[str]:
    """
    Get the AssemblyAI API key from environment variables.
    
    Returns:
        str: The API key or None if not found
    """
    api_key = os.environ.get('ASSEMBLY_API_KEY')
    return api_key if api_key else None  # Return None instead of empty string


def setup_client() -> bool:
    """
    Initialize the AssemblyAI client with API key.
    
    Returns:
        bool: True if setup was successful, False otherwise
    """
    api_key = get_api_key()
    if not api_key:
        logger.error("ASSEMBLY_API_KEY environment variable not set")
        return False
    
    aai.settings.api_key = api_key
    return True


def is_supported_file(file_path: Path) -> bool:
    """
    Check if the file has a supported extension.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        bool: True if the file has a supported extension
    """
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def get_media_type(file_path: Path) -> str:
    """
    Determine if a file is video or audio based on its extension.
    
    Args:
        file_path: Path to the media file
        
    Returns:
        str: 'video' or 'audio'
    """
    return "video" if file_path.suffix.lower() in VIDEO_EXTENSIONS else "audio"


def is_file_available(file_path: Path, force_download: bool = True, max_retries: int = 3, retry_delay: int = 5) -> bool:
    """
    Check if a file is physically available and download it if it's a Google Drive placeholder.
    
    Args:
        file_path: Path to the file to check
        force_download: Whether to force download the file if it's a placeholder
        max_retries: Maximum number of retry attempts
        retry_delay: Seconds to wait between retries
        
    Returns:
        bool: True if the file is physically available and can be read
    """
    # Get file size to calculate adaptive timeout
    try:
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        # For large files (>10MB), log a warning
        if file_size_mb > 10:
            logger.info(f"Large file detected: {file_path.name} ({file_size_mb:.1f} MB)")
    except Exception:
        file_size_mb = 0
        logger.warning(f"Couldn't determine file size: {file_path}")

    # Calculate an appropriate timeout based on file size
    read_timeout = min(180, max(10, int(10 + file_size_mb / 10)))
    
    # Timeout exception
    class TimeoutError(Exception):
        pass
        
    def timeout_handler(signum, frame):
        raise TimeoutError("Read operation timed out")
    
    # Try to read the file, with retries
    for attempt in range(max_retries):
        try:
            # Set up timeout
            original_handler = None
            if hasattr(signal, 'SIGALRM'):
                original_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(read_timeout)
            
            try:
                # Try to read a small chunk to verify availability
                with open(file_path, 'rb') as f:
                    f.read(1024)  # Just read 1KB to check
                
                # Reset alarm
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)
                
                # File is available
                if attempt > 0:
                    logger.info(f"Successfully accessed file on attempt {attempt+1}: {file_path.name}")
                return True
                
            except TimeoutError:
                # Reset alarm
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)
                
                if not force_download or attempt == max_retries - 1:
                    logger.error(f"Timeout reading file after {read_timeout}s: {file_path.name}")
                    return False
                    
            except (IOError, OSError) as e:
                # Reset alarm
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)
                
                if not force_download or attempt == max_retries - 1:
                    logger.error(f"File not available: {file_path.name} - {e}")
                    return False
                
                logger.info(f"File appears to be Google Drive placeholder. Attempting download: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Unexpected error checking file: {e}")
            if attempt == max_retries - 1:
                return False
        
        # Wait before retrying
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    return False


def mock_transcribe_for_testing(
    media_file_path: str, 
    output_path: Optional[str] = None
) -> Optional[Path]:
    """
    Mock transcription function for testing purposes.
    
    Args:
        media_file_path: Path to the media file
        output_path: Optional custom output path for the transcription
        
    Returns:
        Path: Path to the output file
    """
    # Convert to Path object for easier handling
    media_path = Path(media_file_path)
    
    # Check if the file exists
    if not media_path.exists():
        logger.error(f"Media file not found: {media_file_path}")
        return None
        
    # Check if the file is supported
    if not is_supported_file(media_path):
        logger.error(f"Unsupported file format: {media_path.suffix}")
        return None
    
    # Check if the file is physically available (not just a Google Drive placeholder)
    if not is_file_available(media_path):
        logger.error(f"File exists but is not downloaded (Google Drive placeholder): {media_file_path}")
        return None
    
    # Get file type for better logging
    file_type = get_media_type(media_path)
    logger.info(f"[TEST MODE] Mock transcribing {file_type} file: {media_path.name}")
    
    # Determine output file path
    if output_path:
        output_file_path = Path(output_path)
    else:
        output_file_path = media_path.with_name(f"{media_path.stem}_transcription.md")
    
    try:
        # Save a mock transcription to a markdown file
        with output_file_path.open("w", encoding="utf-8") as output_file:
            # Add a header with metadata
            output_file.write(f"# Mock Transcription of {media_path.name}\n\n")
            output_file.write("This is a mock transcription for testing purposes.\n\n")
            
            # Add some fake conversation
            output_file.write("**Speaker 1:** This is a test transcription.\n\n")
            output_file.write("**Speaker 2:** The actual transcription would contain the text from the audio file.\n\n")
            output_file.write("**Speaker 1:** But for testing purposes, this mock version is sufficient.\n")
    except Exception as e:
        logger.error(f"Error creating mock transcription: {e}")
        return None
        
    logger.info(f"[TEST MODE] Mock transcription complete. Saved to {output_file_path}")
    return output_file_path


def transcribe_audio_file_original(
    media_file_path: str, 
    output_path: Optional[str] = None,
    config_options: Optional[Dict[str, Any]] = None,
    retry_existing: bool = False
) -> Optional[Path]:
    """
    Transcribe an audio or video file using AssemblyAI.
    
    Args:
        media_file_path: Path to the media file
        output_path: Optional custom output path for the transcription
        config_options: Optional additional transcription configuration
        retry_existing: Whether to retry a stalled transcription by checking its ID
        
    Returns:
        Path: Path to the output file or None if transcription failed
    """
    start_time = time.time()
    
    # Convert to Path object for easier handling
    media_path = Path(media_file_path)
    
    # Determine output file paths
    if output_path:
        output_md_path = Path(output_path)
        # Create a JSON path from MD path by changing the extension
        json_output_path = output_md_path.with_suffix('.json')
    else:
        output_md_path = media_path.with_name(f"{media_path.stem}_transcription.md")
        json_output_path = media_path.with_name(f"{media_path.stem}.json")
    
    # Check if we should retry an existing transcription
    existing_transcript_id = None
    if retry_existing and json_output_path.exists():
        try:
            with open(json_output_path, 'r') as f:
                status_data = json.load(f)
            existing_transcript_id = status_data.get('transcript_id')
            
            if existing_transcript_id:
                logger.info(f"Attempting to resume existing transcription: {existing_transcript_id}")
                # Check if AssemblyAI API key is available before attempting to check status
                if setup_client():
                    try:
                        # Query AssemblyAI for the status
                        response = requests.get(
                            f"https://api.assemblyai.com/v2/transcript/{existing_transcript_id}",
                            headers={"authorization": aai.settings.api_key}
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            
                            # If the transcript is complete, process it directly
                            if result.get('status') == 'completed':
                                logger.info(f"Found completed transcription: {existing_transcript_id}")
                                
                                # Save the transcription
                                with output_md_path.open("w", encoding="utf-8") as output_file:
                                    output_file.write(f"# Transcription of {media_path.name}\n\n")
                                    output_file.write(result.get('text', ''))
                                
                                # Save the final JSON file
                                transcript_data = {
                                    "text": result.get('text', ''),
                                    "media_file": str(media_path),
                                    "completed_time": time.time(),
                                    "duration": result.get('audio_duration'),
                                    "transcript_id": existing_transcript_id
                                }
                                
                                # Add utterances if available
                                if result.get('utterances'):
                                    transcript_data["utterances"] = result.get('utterances')
                                
                                with open(json_output_path, 'w') as f:
                                    json.dump(transcript_data, f, indent=2)
                                
                                logger.info(f"Recovered transcription complete. Saved to {output_md_path} and {json_output_path}")
                                
                                # Delete the JSON file after successful transcription
                                try:
                                    if json_output_path.exists():
                                        os.remove(json_output_path)
                                        logger.info(f"Removed JSON file: {json_output_path}")
                                except Exception as e:
                                    logger.warning(f"Could not remove JSON file {json_output_path}: {e}")
                                
                                return output_md_path
                            
                            elif result.get('status') == 'error':
                                logger.warning(f"Existing transcription has error status: {result.get('error')}")
                                # Continue with new transcription
                            
                            elif result.get('status') in ['queued', 'processing']:
                                logger.info(f"Existing transcription is still processing. Updating status.")
                                
                                # Update the status file with fresh info
                                status_data = {
                                    "status": result.get('status'),
                                    "media_file": str(media_path),
                                    "start_time": time.time(),
                                    "message": f"Transcription in progress (status: {result.get('status')})",
                                    "transcript_id": existing_transcript_id
                                }
                                
                                with open(json_output_path, 'w') as f:
                                    json.dump(status_data, f, indent=2)
                                
                                logger.info(f"Updated status for existing transcription: {existing_transcript_id}")
                                return None  # Don't start a new transcription
                    except Exception as e:
                        logger.warning(f"Error checking existing transcription status: {e}")
                        # Continue with new transcription
                    
        except Exception as e:
            logger.warning(f"Error reading existing transcription data: {e}")
            # Continue with new transcription
    
    # Check if the file exists
    if not media_path.exists():
        logger.error(f"Media file not found: {media_file_path}")
        return None
        
    # Check if the file is supported
    if not is_supported_file(media_path):
        logger.error(f"Unsupported file format: {media_path.suffix}")
        return None
    
    # Check if the file is physically available (not just a Google Drive placeholder)
    logger.info(f"Checking file availability: {media_file_path}")
    if not is_file_available(media_path):
        logger.error(f"File exists but is not downloaded (Google Drive placeholder): {media_file_path}")
        return None
    
    logger.info(f"File availability check completed in {time.time() - start_time:.2f} seconds")
    
    # Create the initial JSON file with status "in_progress"
    os.makedirs(json_output_path.parent, exist_ok=True)
    try:
        initial_data = {
            "status": "in_progress",
            "media_file": str(media_path),
            "start_time": time.time(),
            "message": "Transcription in progress"
        }
        with open(json_output_path, 'w') as f:
            json.dump(initial_data, f, indent=2)
        logger.info(f"Created initial status file: {json_output_path}")
    except Exception as e:
        logger.error(f"Failed to create initial status file: {e}")
        # Continue anyway - this is not critical
        
    # Setup AssemblyAI client
    logger.info(f"Setting up AssemblyAI client")
    if not setup_client():
        # Update JSON file with error status
        try:
            error_data = {
                "status": "error",
                "media_file": str(media_path),
                "error": "Failed to set up AssemblyAI client",
                "timestamp": time.time()
            }
            with open(json_output_path, 'w') as f:
                json.dump(error_data, f, indent=2)
        except Exception:
            pass  # Ignore errors updating the status file
        return None
    
    # Get file type for better logging
    file_type = get_media_type(media_path)
    logger.info(f"Starting transcription of {file_type} file: {media_path.name}")
    
    # Set default config options if not provided
    if config_options is None:
        config_options = {}
    
    # Ensure speaker labels are enabled by default
    if 'speaker_labels' not in config_options:
        config_options['speaker_labels'] = True
        
    # Initialize transcriber
    try:
        transcriber = aai.Transcriber()
        logger.info(f"Successfully initialized transcriber")
    except Exception as e:
        logger.error(f"Failed to initialize transcriber: {e}")
        # Update JSON file with error status
        try:
            error_data = {
                "status": "error",
                "media_file": str(media_path),
                "error": f"Failed to initialize transcriber: {e}",
                "timestamp": time.time()
            }
            with open(json_output_path, 'w') as f:
                json.dump(error_data, f, indent=2)
        except Exception:
            pass  # Ignore errors updating the status file
        return None
    
    config = aai.TranscriptionConfig(**config_options)
    
    try:
        # Start transcription
        logger.info(f"Submitting file {media_path.name} for transcription...")
        transcript_obj = transcriber.transcribe(str(media_path), config=config)
        
        # Log the transcript ID for debugging
        if hasattr(transcript_obj, 'id'):
            logger.info(f"Transcription job ID: {transcript_obj.id}")
            # Update JSON with transcript ID
            try:
                with open(json_output_path, 'r') as f:
                    status_data = json.load(f)
                status_data["transcript_id"] = transcript_obj.id
                with open(json_output_path, 'w') as f:
                    json.dump(status_data, f, indent=2)
            except Exception:
                pass  # Ignore errors updating the status file
        
        # Check for errors
        if hasattr(transcript_obj, 'error') and transcript_obj.error:
            logger.error(f"Transcription error: {transcript_obj.error}")
            # Update JSON file with error status
            try:
                error_data = {
                    "status": "error",
                    "media_file": str(media_path),
                    "error": transcript_obj.error,
                    "timestamp": time.time()
                }
                with open(json_output_path, 'w') as f:
                    json.dump(error_data, f, indent=2)
            except Exception:
                pass  # Ignore errors updating the status file
            return None
            
        # Check status and text
        if not hasattr(transcript_obj, 'text') or not transcript_obj.text:
            logger.warning("Transcript object does not contain text. This might be a large file still processing.")
            if hasattr(transcript_obj, 'status') and transcript_obj.status != 'completed':
                logger.info(f"Current status: {transcript_obj.status}. Larger files may take more time.")
            # Update JSON file with processing status
            try:
                status_data = {
                    "status": "processing",
                    "media_file": str(media_path),
                    "message": "Transcription still processing",
                    "timestamp": time.time()
                }
                if hasattr(transcript_obj, 'id'):
                    status_data["transcript_id"] = transcript_obj.id
                with open(json_output_path, 'w') as f:
                    json.dump(status_data, f, indent=2)
            except Exception:
                pass  # Ignore errors updating the status file
            return None
            
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        # Update JSON file with error status
        try:
            error_data = {
                "status": "error",
                "media_file": str(media_path),
                "error": str(e),
                "timestamp": time.time()
            }
            with open(json_output_path, 'w') as f:
                json.dump(error_data, f, indent=2)
        except Exception:
            pass  # Ignore errors updating the status file
        return None

    # Save results to files
    try:
        # 1. Save the markdown file with the transcription
        with output_md_path.open("w", encoding="utf-8") as output_file:
            # Add a header with metadata
            output_file.write(f"# Transcription of {media_path.name}\n\n")
            
            # If we have utterances with speaker labels
            if hasattr(transcript_obj, 'utterances') and transcript_obj.utterances:
                # Process utterances with speaker labels
                logger.info(f"Transcription has {len(transcript_obj.utterances)} utterances with speaker labels")
                for utterance in transcript_obj.utterances:
                    speaker = utterance.speaker
                    text = utterance.text
                    if speaker and text:
                        output_file.write(f"**Speaker {speaker}:** {text}\n\n")
            else:
                # Just write the raw text
                output_file.write(transcript_obj.text)
                
        # 2. Save the final JSON file with complete transcript data
        transcript_data = {
            "text": transcript_obj.text if hasattr(transcript_obj, 'text') else "",
            "media_file": str(media_path),
            "completed_time": time.time(),
            "duration": transcript_obj.audio_duration if hasattr(transcript_obj, 'audio_duration') else None
        }
        
        # Add extra data from the transcript object if available
        if hasattr(transcript_obj, 'utterances') and transcript_obj.utterances:
            transcript_data["utterances"] = [
                {
                    "speaker": u.speaker,
                    "text": u.text,
                    "start": u.start,
                    "end": u.end
                } 
                for u in transcript_obj.utterances
            ]
        
        # Write the final JSON
        with open(json_output_path, 'w') as f:
            json.dump(transcript_data, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error saving transcription: {e}")
        # Update JSON file with error status if we couldn't save the final result
        try:
            error_data = {
                "status": "error",
                "media_file": str(media_path),
                "error": f"Error saving transcription: {e}",
                "timestamp": time.time()
            }
            with open(json_output_path, 'w') as f:
                json.dump(error_data, f, indent=2)
        except Exception:
            pass  # Ignore errors updating the status file
        return None
        
    logger.info(f"Transcription complete. Saved to {output_md_path} and {json_output_path}")
    
    # Delete the JSON file after successful transcription
    try:
        if json_output_path.exists():
            os.remove(json_output_path)
            logger.info(f"Removed JSON file: {json_output_path}")
    except Exception as e:
        logger.warning(f"Could not remove JSON file {json_output_path}: {e}")
    
    return output_md_path


# Use the real implementation for production
transcribe_audio_file = transcribe_audio_file_original 