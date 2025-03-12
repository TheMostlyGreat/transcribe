# Transcribe

A simple media transcription CLI that converts audio and video files to text with diarization and speaker labels using AssemblyAI.

## Features

- Transcribe both audio and video files
- Support for numerous media formats:
  - Audio: mp3, wav, m4a, flac, aac, ogg, wma, aiff, alac
  - Video: mp4, mov, avi, wmv, webm, mkv, mpg, mpeg, m4v, asf, dv, ogv, vp8
- Speaker diarization (identifying who said what)
- Easy-to-use command-line interface
- Batch processing for multiple files
- Optional email notifications when transcriptions complete

## Installation

```bash
# Install from source
git clone https://github.com/alex-salazar/transcribe.git
cd transcribe
pip install -e .
```

After installation, verify the package is installed correctly:

```bash
pip list | grep transcribe
```

## Requirements

- Python 3.7+
- AssemblyAI API key (set as environment variable `ASSEMBLY_API_KEY`)

## Usage

### Single File Transcription

```bash
# Transcribe a single file
python -m transcribe file path/to/media_file.mp3

# With custom output path
python -m transcribe file path/to/media_file.mp3 --output path/to/output.md

# Enable verbose logging
python -m transcribe file path/to/media_file.mp3 --verbose
```

### Batch Processing

```bash
# Process all new media files in a directory
python -m transcribe batch path/to/directory

# With email notifications
python -m transcribe batch path/to/directory --email
```

For email notifications, set the following environment variables:
- `SMTP_SERVER` - SMTP server address
- `SMTP_PORT` - SMTP port (default: 587)
- `SMTP_USERNAME` - SMTP username
- `SMTP_PASSWORD` - SMTP password
- `EMAIL_FROM` - Sender email address
- `EMAIL_TO` - Recipient email address

## Help

```bash
# Show general help
python -m transcribe --help

# Show help for a specific command
python -m transcribe file --help
python -m transcribe batch --help
```

## Automation with Cron

You can automate transcription of new media files using cron jobs:

```bash
# Create a copy of the example script and customize it
cp run_transcribe_example.sh run_transcribe.sh
chmod +x run_transcribe.sh
```

Edit `run_transcribe.sh` to:
1. Set the path to your media directory
2. Configure your Python environment
3. Set your API key and email settings if needed

Then set up a cron job:

```bash
# Open crontab editor
crontab -e

# Add a line to run the script every minute
* * * * * /path/to/your/run_transcribe.sh

# Save and exit (in vi: press Esc, type :wq, press Enter)
```

For less frequent runs, adjust the cron timing:
- `*/5 * * * *` - every 5 minutes
- `0 * * * *` - every hour
- `0 0 * * *` - daily at midnight

## Troubleshooting

### Command Not Found
If you encounter an error like `command not found: transcribe`, use the module invocation pattern with Python:
```bash
python -m transcribe [command] [options]
```

### API Key Issues
If you encounter authentication errors, verify your AssemblyAI API key is set correctly:
```bash
# Check if environment variable is set
echo $ASSEMBLY_API_KEY

# Set the API key if needed
export ASSEMBLY_API_KEY="your_api_key_here"
```

### Path Issues in Automation Script
If using the automation script, ensure all paths are correct and absolute. Verify paths with:
```bash
# Check media directory exists
ls -la /path/to/your/media/directory

# Check project directory exists
ls -la /path/to/transcribe/project
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](LICENSE)
