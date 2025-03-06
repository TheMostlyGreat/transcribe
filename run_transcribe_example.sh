#!/bin/bash

# Script for scheduling regular transcription batch processing
# Customize this file and use with cron for automated media processing

# Set path to your Python environment
# If using a virtual environment, uncomment and modify this line:
# source /path/to/your/venv/bin/activate

# Set your AssemblyAI API key if not already in environment
# export ASSEMBLY_API_KEY="your_api_key_here"

# Set email configuration if needed
# export SMTP_SERVER="smtp.example.com"
# export SMTP_PORT=587
# export SMTP_USERNAME="your_username"
# export SMTP_PASSWORD="your_password"
# export EMAIL_FROM="sender@example.com"
# export EMAIL_TO="recipient@example.com"

# Directory to process (customize this path)
MEDIA_DIR="/path/to/your/media/directory"

# Path to the project root
PROJECT_DIR="/path/to/transcribe/project"

# Run the transcription batch process
cd "$PROJECT_DIR"
python -m transcribe batch "$MEDIA_DIR" 2>&1 >> ~/Library/Logs/transcribe.log

# Add date/time stamp to log
echo "Batch process completed at $(date)" >> ~/Library/Logs/transcribe.log 