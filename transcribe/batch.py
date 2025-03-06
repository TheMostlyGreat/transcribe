"""
Batch processing module for transcribing multiple media files in a directory.
"""

import os
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from transcribe.core import transcribe_audio_file, is_supported_file, get_media_type

# Configure module logger
logger = logging.getLogger(__name__)


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
    # Get email configuration
    config = get_email_config()
    
    # Validate configuration
    if not validate_email_config(config):
        logger.error("Email configuration incomplete. Set all required environment variables.")
        return False
    
    # Prepare email message
    file_type = get_media_type(media_file)
    subject = f"Transcription Completed: {media_file.name}"
    body = (
        f"The {file_type} file {media_file.name} has been transcribed.\n"
        f"Transcription saved at: {transcription_file}\n"
    )
    
    # Create email message
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = config['email_from']
    message['To'] = config['email_to']
    message.set_content(body)
    
    try:
        # Send email
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['smtp_username'], config['smtp_password'])
            server.send_message(message)
        
        logger.info(f"Email notification sent for {media_file.name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email for {media_file.name}: {e}")
        return False


def find_new_media_files(directory: str) -> List[Tuple[Path, Optional[Path]]]:
    """
    Find media files in a directory that haven't been transcribed yet.
    
    Args:
        directory: Path to the directory to scan
        
    Returns:
        List of tuples containing (media_file_path, expected_transcription_path)
    """
    # Convert to Path object
    directory_path = Path(directory)
    
    if not directory_path.is_dir():
        logger.error(f"Not a directory: {directory}")
        return []
    
    # Find all media files and check for existing transcriptions
    result = []
    for file_path in directory_path.iterdir():
        if file_path.is_file() and is_supported_file(file_path):
            # Check if a transcription file already exists
            expected_output = file_path.with_name(f"{file_path.stem}_transcription.md")
            
            if expected_output.exists():
                logger.debug(f"Skipping {file_path.name} - already transcribed")
            else:
                result.append((file_path, expected_output))
    
    return result


def process_folder(directory: str, send_emails: bool = False) -> Tuple[bool, int]:
    """
    Process all new media files in a directory.
    
    Args:
        directory: Path to the directory
        send_emails: Whether to send email notifications
        
    Returns:
        tuple: (success_status, processed_count) where:
            - success_status is True if all files were processed successfully
            - processed_count is the number of files that were transcribed
    """
    # Find media files to process
    media_files = find_new_media_files(directory)
    
    if not media_files:
        # Silent operation when nothing to process
        return True, 0
    
    logger.info(f"Found {len(media_files)} new media files to process")
    
    # Process each file
    success_count = 0
    for media_file, expected_output in media_files:
        logger.info(f"Processing {media_file.name}...")
        
        # Transcribe the file
        result = transcribe_audio_file(str(media_file))
        
        if result:
            success_count += 1
            
            # Send email notification if requested
            if send_emails:
                send_email_alert(media_file, result)
        else:
            logger.error(f"Failed to transcribe {media_file.name}")
    
    # Report results
    if success_count == len(media_files):
        logger.info(f"Successfully processed all {len(media_files)} files")
        return True, success_count
    else:
        logger.warning(f"Processed {success_count} of {len(media_files)} files successfully")
        return False, success_count 