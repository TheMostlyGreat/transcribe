# Transcribe Tests

This directory contains all tests for the Transcribe project.

## Directory Structure

- `tests/` - Main test directory
  - `test_*.py` - Standard pytest test modules
  - `conftest.py` - pytest fixtures
  - `mocks.py` - Mock objects for testing
  - `run_all_tests.py` - Script to run all tests
  - `test_data/` - Test resources and data files
    - Audio test files
    - Transcription examples
    - Batch test data
  - `scripts/` - Shell scripts for integration testing
    - `test_empty_run.sh` - Tests batch processing with no files
    - `test_with_files_run.sh` - Tests batch processing with files

## Pytest Best Practices

This project follows these pytest best practices:

1. **Simple, focused tests**: Each test checks one thing
2. **Proper fixtures**: Use fixtures for setup and teardown
3. **No testing implementation details**: Test the API, not internals
4. **Good naming conventions**: Clear test names that describe what's being tested
5. **Isolation**: Tests run independently and don't affect each other
6. **Configuration in pytest.ini**: Centralized configuration for consistent behavior
7. **Test categorization**: Tests are marked by type (unit, integration, api, slow)

### Fixture Usage

Fixtures in conftest.py provide:
- `mock_transcriber` - Mocked version of the AssemblyAI transcription API
- `test_audio_file` - Temporary audio file for testing
- `debug_info` - Helper for debugging import/test issues (opt-in only)

### Test Markers

Tests are categorized with markers to allow selective running:

- `unit` - Fast tests that check individual functions
- `integration` - Tests that check multiple components together
- `api` - Tests that require the AssemblyAI API
- `slow` - Tests that take longer than 1 second to run

### Monkeypatching Guidelines

When patching functions or attributes:
- Use the built-in monkeypatch fixture
- Patch at the target module level, not import site
- Keep patches scoped to just the test that needs them

## Known Issues and Todo Items

Some tests have issues that need to be addressed:

1. **Import problems with `__version__`**: Many tests fail when trying to import modules that depend on `__version__` in `__init__.py`. 
   
   Solution approaches:
   - Mark these tests with `@pytest.mark.xfail` as done in `test_imports.py`
   - Modify the tests to use direct file access for testing code existence instead of imports
   - Fix the package to ensure `__version__` is always available

2. **Redundant test files**: Several tests check the same functionality.

   Todo:
   - Consolidate tests to avoid duplication
   - Apply test markers to all tests
   - Ensure complete coverage of all modules

3. **Integration vs Unit tests**: Not all tests are properly categorized.

   Todo:
   - Add appropriate markers to all test files
   - Identify slow tests and mark them accordingly

## Running Tests

### Using pytest

```bash
# Run all pytest tests
pytest

# Run with coverage report (not in pytest.ini)
pytest --cov=transcribe --cov-report=term-missing

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run a specific test file
pytest tests/test_core.py

# Run a specific test
pytest tests/test_core.py::test_get_api_key
```

### Using the test runner

```bash
# Run all tests (pytest + standalone)
python -m tests.run_all_tests

# Run only standalone tests
python -m tests.run_all_tests --standalone-only
```

### Individual test scripts

Some tests are standalone scripts that can be run directly:

```bash
# Run placeholder file test
python -m tests.test_placeholder

# Run status tracking test
python -m tests.test_status_tracking
```

### Shell-based integration tests

The project includes shell scripts for integration testing:

```bash
# Test batch processing with no files (should not create log)
./tests/scripts/test_empty_run.sh

# Test batch processing with files (should create log)
./tests/scripts/test_with_files_run.sh
```

These shell scripts test the CLI functionality directly, verifying behavior with
empty directories and directories containing media files. 