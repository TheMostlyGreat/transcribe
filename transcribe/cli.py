"""
Command-line interface for the transcribe package.
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

# Try to import version, but don't fail if unavailable
try:
    from transcribe import __version__
except ImportError:
    __version__ = "0.1"  # Fallback version

from transcribe.core import transcribe_audio_file, SUPPORTED_EXTENSIONS
from transcribe.batch import process_folder


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging based on verbosity level.
    Also deletes log files older than one month.
    
    Args:
        verbose: Whether to enable verbose (DEBUG) logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger - force set level
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Delete log files older than one month
    cleanup_old_logs(logs_dir)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"transcribe_{timestamp}.log"
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Log the start of the application
    logging.info(f"Logging started - output file: {log_file}")


def cleanup_old_logs(logs_dir: Path) -> None:
    """
    Deletes log files older than one month from the specified directory.
    
    Args:
        logs_dir: Path to the logs directory
    """
    try:
        # Calculate the cutoff date (one month ago)
        cutoff_date = datetime.now() - timedelta(days=30)
        
        # Get all log files
        log_files = list(logs_dir.glob("transcribe_*.log"))
        
        # Track stats for logging
        deleted_count = 0
        
        for log_file in log_files:
            # Get file modification time
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            # Delete if older than the cutoff date
            if file_time < cutoff_date:
                log_file.unlink()
                deleted_count += 1
        
        if deleted_count > 0:
            logging.info(f"Deleted {deleted_count} log files older than one month")
            
    except Exception as e:
        # Log error but don't interrupt the program
        logging.warning(f"Error cleaning up old logs: {e}")


def display_supported_formats() -> str:
    """
    Format the supported file extensions for display.
    
    Returns:
        str: Formatted string of supported extensions
    """
    extensions = sorted(list(SUPPORTED_EXTENSIONS))
    return ", ".join(ext.lstrip('.') for ext in extensions)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: Command-line arguments (uses sys.argv if None)
        
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description=f"Transcribe v{__version__}: Convert audio and video files to text with speaker diarization.",
        epilog=f"Supported formats: {display_supported_formats()}",
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Single file transcription command
    transcribe_parser = subparsers.add_parser(
        "file", 
        help="Transcribe a single media file"
    )
    transcribe_parser.add_argument(
        "media_file", 
        help="Path to the input audio or video file"
    )
    transcribe_parser.add_argument(
        "--output", "-o",
        help="Custom output file path (default: same location as input with _transcription.md suffix)",
    )
    
    # Batch processing command
    batch_parser = subparsers.add_parser(
        "batch", 
        help="Process multiple files in a directory"
    )
    batch_parser.add_argument(
        "directory", 
        help="Directory containing media files to transcribe"
    )
    batch_parser.add_argument(
        "--email", "-e",
        action="store_true",
        help="Send email notifications when transcriptions complete",
    )
    
    # Global options
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    # Parse arguments
    parsed_args = parser.parse_args(args)
    
    # Default to file command if no command specified but media_file is provided
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists() and parsed_args.command is None:
        parsed_args.command = "file"
        parsed_args.media_file = sys.argv[1]
    
    return parsed_args


def cli_main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the command-line interface.
    
    Args:
        args: Command-line arguments (uses sys.argv if None)
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse arguments
    parsed_args = parse_args(args)
    
    # Setup logging
    setup_logging(parsed_args.verbose)
    
    # Get logger for this module
    logger = logging.getLogger(__name__)
    
    # Process commands
    if parsed_args.command == "file":
        # Transcribe a single file
        result = transcribe_audio_file(
            parsed_args.media_file,
            output_path=getattr(parsed_args, "output", None),
        )
        return 0 if result else 1
    
    elif parsed_args.command == "batch":
        # Process files in a directory
        send_emails = getattr(parsed_args, "email", False)
        result = process_folder(
            parsed_args.directory,
            send_emails=send_emails,
        )
        
        # Process folder returns a tuple of (success, processed_count)
        if isinstance(result, tuple) and len(result) == 2:
            success, processed_count = result
            if processed_count > 0:
                return 0 if success else 1
            else:
                logger.warning("No files were processed")
                return 0  # No files is not an error
        else:
            # Handle backward compatibility with older versions that returned just a boolean
            return 0 if result else 1
    
    # If we get here, no command was specified
    logger.error("No command specified")
    return 1


if __name__ == "__main__":
    sys.exit(cli_main()) 