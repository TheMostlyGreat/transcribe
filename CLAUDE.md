# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python CLI tool for transcribing audio and video files using AssemblyAI's API. Supports both single file and batch processing with speaker diarization, email notifications, and status tracking.

## Commands

### Development & Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m "not api"     # Exclude API tests (no real API calls)

# Run specific test file
pytest tests/test_core.py

# Run with verbose output
pytest -v

# Install package in development mode
pip install -e .
```

### Running the Application

```bash
# Single file transcription
python -m transcribe file path/to/media.mp3
python -m transcribe file path/to/media.mp3 --output custom_path.md
python -m transcribe file path/to/media.mp3 --verbose

# Batch processing
python -m transcribe batch path/to/directory
python -m transcribe batch path/to/directory --email

# Show help
python -m transcribe --help
python -m transcribe file --help
python -m transcribe batch --help
```

## Architecture

### Module Structure

```
transcribe/
├── __init__.py         # Package initialization, exports main()
├── __main__.py         # Entry point for python -m transcribe
├── cli.py              # CLI argument parsing, logging setup
├── core.py             # Core transcription logic and file handling
├── batch.py            # Batch processing and email notifications
└── version.py          # Version number
```

### Key Design Patterns

**Google Drive File Handling:**
- Files in Google Drive may be "placeholders" (not fully downloaded)
- `is_file_available()` in `core.py` detects and handles this by attempting reads with retries
- Uses adaptive timeouts based on file size (larger files get more time)
- Critical for batch processing to avoid processing unavailable files

**Status Tracking with JSON Files:**
- Each transcription creates a `.json` status file alongside the media file
- Status values: `in_progress`, `processing`, `completed`, `error`
- Includes `transcript_id` from AssemblyAI for recovery/retry
- JSON deleted after successful completion, MD file remains
- Stalled transcriptions (>24 hours old) are automatically detected and retried

**Progress Monitoring Decorator:**
- `@progress_monitor(name)` decorator in `core.py` tracks long operations
- Updates global `_operation_status` dict with timestamps and thread info
- Background thread logs progress every 10 seconds
- Used for debugging slow operations

**Mock Mode for Testing:**
- `mock_transcribe_for_testing()` provides offline testing without API calls
- Can be swapped in place of real transcription function
- Important: Real implementation is `transcribe_audio_file_original`, assigned to `transcribe_audio_file`

### Critical Gotchas

**Path Handling:**
- Codebase runs in Google Drive paths with spaces: `"My Drive/Projects/transcribe"`
- ALWAYS use `Path` objects from `pathlib`, never string concatenation
- Test with paths containing spaces to ensure compatibility

**AssemblyAI API Key:**
- Required env var: `ASSEMBLY_API_KEY`
- `setup_client()` must be called before any transcription
- Mock module created if `assemblyai` import fails (for testing)

**Email Configuration:**
- Requires ALL of: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO`
- `validate_email_config()` checks all required fields
- Missing config fails gracefully without crashing

**Logging:**
- Logs saved to `logs/transcribe_{timestamp}.log`
- Auto-cleanup: deletes logs older than 30 days
- Verbosity controlled by `--verbose` flag (INFO vs DEBUG)
- Both console and file handlers configured

### Test Organization

**Pytest Markers:**
- `@pytest.mark.unit` - Pure logic tests, no external dependencies
- `@pytest.mark.integration` - Multiple components, may use mocks
- `@pytest.mark.api` - Requires real AssemblyAI API calls (expensive/slow)
- `@pytest.mark.slow` - Takes >1 second

**Key Fixtures (conftest.py):**
- `test_files_dir` - Points to `tests/test_data/`
- `test_audio_file` - Path to sample MP3
- `temp_dir` - Auto-cleanup temporary directory
- `temp_batch_dir` - Temp dir with 3 copied audio files
- `mock_env_vars` - Sets up all required env vars for testing

**Testing Strategy:**
- Use `mock_transcribe_for_testing()` to avoid API costs
- Integration tests should mock external APIs
- API tests should be marked and run separately in CI only

## Supported File Formats

**Audio:** mp3, wav, m4a, flac, aac, ogg, wma, aiff, alac
**Video:** mp4, mov, avi, wmv, webm, mkv, mpg, mpeg, m4v, asf, dv, ogv, vp8

Constants: `AUDIO_EXTENSIONS`, `VIDEO_EXTENSIONS`, `SUPPORTED_EXTENSIONS` in `core.py`
