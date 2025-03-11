"""
Batch processing module for transcribing multiple media files in a directory.
"""

import os
import logging
import time
import json
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from transcribe.core import (
    transcribe_audio_file, 
    is_supported_file, 
    get_media_type, 
    is_file_available
)

# Configure module logger
logger = logging.getLogger(__name__)

# Default maximum file size in MB (0 means no limit)
DEFAULT_MAX_FILE_SIZE_MB = 0

# Maximum age for in-progress transcription files (in hours)
MAX_IN_PROGRESS_AGE_HOURS = 24


def get_email_config() -> Dict[str, Any]:
    """
    Get email configuration from environment variables.
    
    Returns:
        dict: Email configuration parameters
    """
    config = {
        'smtp_server': os.getenv('SMTP_SERVER'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_username': os.getenv('SMTP_USERNAME'),
        'smtp_password': os.getenv('SMTP_PASSWORD'),
        'email_from': os.getenv('EMAIL_FROM'),
        'email_to': os.getenv('EMAIL_TO'),
    }
    
    return config


def validate_email_config(config: Dict[str, Any]) -> bool:
    """
    Check if email configuration is valid.
    
    Args:
        config: Email configuration dictionary
        
    Returns:
        bool: True if configuration is valid
    """
    required_fields = ['smtp_server', 'smtp_username', 'smtp_password', 'email_from', 'email_to']
    return all(config.get(field) for field in required_fields)


def send_email_alert(media_file: Path, transcription_file: Path) -> bool:
    """
    Send an email notification for a completed transcription.
    
    Args:
        media_file: Path to the original media file
        transcription_file: Path to the transcription file
        
    Returns:
        bool: True if email was sent successfully
    """
    config = get_email_config()
    
    if not validate_email_config(config):
        logger.error("Email configuration is incomplete. Check environment variables.")
        return False
    
    try:
        # Create the email
        message = EmailMessage()
        message['Subject'] = f'Transcription Complete: {media_file.name}'
        message['From'] = config['email_from']
        message['To'] = config['email_to']
        
        # Create email body
        body = f"""
        Transcription of {media_file.name} is complete.
        
        File: {transcription_file}
        Created: {transcription_file.stat().st_mtime}
        Size: {transcription_file.stat().st_size / 1024:.1f} KB
        """
        message.set_content(body)
        
        # Send the email
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['smtp_username'], config['smtp_password'])
            server.send_message(message)
            
        logger.info(f"Email notification sent for {media_file.name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email for {media_file.name}: {e}")
        return False


def find_new_media_files(directory: str, force_download: bool = True, max_file_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB) -> List[Tuple[Path, Optional[Path]]]:
    """
    Find media files in a directory that haven't been transcribed yet.
    
    Args:
        directory: Path to the directory to scan
        force_download: Whether to force download Google Drive placeholder files
        max_file_size_mb: Maximum file size in MB to process (0 = no limit)
        
    Returns:
        List of tuples containing (media_file_path, expected_transcription_path)
    """
    # Convert to Path object
    directory_path = Path(directory)
    
    if not directory_path.is_dir():
        logger.error(f"Not a directory: {directory}")
        return []
    
    logger.info(f"Scanning for media files in {directory}")
    
    # Find all media files and check for existing transcriptions
    result = []
    skipped_large_files = []
    large_files = []
    in_progress_files = []
    stalled_files = []
    completed_files = 0
    
    # Calculate cutoff time for stalled transcriptions
    stalled_cutoff = time.time() - (MAX_IN_PROGRESS_AGE_HOURS * 60 * 60)
    
    for file_path in directory_path.iterdir():
        if file_path.is_file() and is_supported_file(file_path):
            # Check file size
            file_size_mb = 0
            try:
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > 100:  # Just log large files 
                    large_files.append((file_path.name, file_size_mb))
                
                # Skip if max_file_size_mb is set and file exceeds it
                if max_file_size_mb > 0 and file_size_mb > max_file_size_mb:
                    logger.warning(f"Skipping {file_path.name} - file too large ({file_size_mb:.2f} MB > {max_file_size_mb} MB limit)")
                    skipped_large_files.append(file_path.name)
                    continue
            except Exception as e:
                logger.warning(f"Couldn't check size of {file_path}: {e}")
            
            # Define expected output paths
            json_path = file_path.with_name(f"{file_path.stem}.json")
            md_path = file_path.with_name(f"{file_path.stem}_transcription.md")
            
            # Check if JSON file exists
            if json_path.exists():
                try:
                    # Read the JSON file to check status
                    with open(json_path, 'r') as f:
                        status_data = json.load(f)
                    
                    # Check if it's in progress
                    if status_data.get('status') == 'in_progress' or status_data.get('status') == 'processing':
                        # Check if it's stalled
                        start_time = status_data.get('start_time', 0)
                        if start_time < stalled_cutoff:
                            logger.warning(f"Found stalled transcription for {file_path.name} - started {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
                            stalled_files.append(file_path.name)
                            result.append((file_path, md_path))
                        else:
                            logger.info(f"Skipping {file_path.name} - transcription in progress")
                            in_progress_files.append(file_path.name)
                    elif status_data.get('status') == 'error':
                        logger.warning(f"Previous transcription for {file_path.name} failed: {status_data.get('error', 'Unknown error')}")
                        # Retry failed transcriptions
                        result.append((file_path, md_path))
                    else:
                        # No status field means it's a completed transcription
                        logger.debug(f"Skipping {file_path.name} - already transcribed")
                        completed_files += 1
                except Exception as e:
                    logger.warning(f"Error reading JSON for {file_path.name}: {e}")
                    # If we can't read the JSON, try to transcribe again
                    result.append((file_path, md_path))
            else:
                # No JSON exists, check for old-style MD file
                if md_path.exists():
                    logger.debug(f"Skipping {file_path.name} - already transcribed (old style)")
                    completed_files += 1
                elif not is_file_available(file_path, force_download=force_download):
                    logger.info(f"Skipping {file_path.name} - file exists but could not be downloaded")
                else:
                    result.append((file_path, md_path))
    
    # Log summary information
    if skipped_large_files:
        logger.info(f"Skipped {len(skipped_large_files)} files exceeding size limit")
    
    if large_files and max_file_size_mb == 0:
        logger.info(f"Found {len(large_files)} large files to process (>100MB)")
        for name, size in large_files:
            logger.info(f"  - {name}: {size:.2f} MB")
    
    if in_progress_files:
        logger.info(f"Found {len(in_progress_files)} files currently being transcribed")
    
    if stalled_files:
        logger.warning(f"Found {len(stalled_files)} stalled transcriptions (older than {MAX_IN_PROGRESS_AGE_HOURS} hours)")
    
    if completed_files > 0:
        logger.info(f"Found {completed_files} already completed transcriptions")
    
    if not result:
        logger.info("No new media files to process")
    else:
        logger.info(f"Found {len(result)} media files to process")
    
    return result


def process_folder(directory: str, send_emails: bool = False, force_download: bool = True, max_file_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB) -> Tuple[bool, int]:
    """
    Process all new media files in a directory.
    
    Args:
        directory: Path to the directory
        send_emails: Whether to send email notifications
        force_download: Whether to force download Google Drive placeholder files
        max_file_size_mb: Maximum file size in MB to process (0 = no limit)
        
    Returns:
        tuple: (success_status, processed_count) where:
            - success_status is True if all files were processed successfully
            - processed_count is the number of files that were transcribed
    """
    # Find media files to process
    media_files = find_new_media_files(directory, force_download=force_download, max_file_size_mb=max_file_size_mb)
    
    if not media_files:
        # Nothing to process
        return True, 0
    
    logger.info(f"Processing {len(media_files)} media files")
    
    # Track successfully processed files
    success_count = 0
    failed_files = []
    
    for media_file, output_path in media_files:
        logger.info(f"Processing {media_file.name}...")
        
        # Check if this might be a stalled transcription
        json_path = media_file.with_name(f"{media_file.stem}.json")
        is_stalled = False
        
        if json_path.exists():
            try:
                with open(json_path, 'r') as f:
                    status_data = json.load(f)
                # Check if it has a status and start_time
                if status_data.get('status') in ['in_progress', 'processing']:
                    # Check if it's older than the stalled cutoff
                    start_time = status_data.get('start_time', 0)
                    stalled_cutoff = time.time() - (MAX_IN_PROGRESS_AGE_HOURS * 60 * 60)
                    if start_time < stalled_cutoff:
                        is_stalled = True
                        logger.info(f"Detected stalled transcription for {media_file.name}")
            except Exception:
                pass
        
        # Transcribe the file, with retry for stalled transcriptions
        result = transcribe_audio_file(
            str(media_file), 
            output_path=str(output_path) if output_path else None,
            retry_existing=is_stalled
        )
        
        if result:
            success_count += 1
            
            # Send email notification if enabled
            if send_emails:
                send_email_alert(media_file, result)
        else:
            failed_files.append(media_file.name)
            logger.error(f"Failed to transcribe {media_file.name}")
    
    # Report results
    if failed_files:
        logger.warning(f"Processed {success_count} of {len(media_files)} files successfully")
        return False, success_count
    else:
        logger.info(f"Successfully processed all {success_count} files")
        return True, success_count 