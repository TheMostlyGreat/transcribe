#!/usr/bin/env python3
"""
Comprehensive test runner for the transcribe project.

This script runs:
1. All pytest-based tests in the tests directory
2. Standalone test scripts for special test cases
3. Shell-based integration tests

Usage:
    python -m tests.run_all_tests [--all] [--standalone-only] [--shell-only]
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def run_pytest():
    """
    Run the standard pytest suite.
    
    Returns:
        int: Exit code from pytest (0 for success)
    """
    print("\n===== Running pytest test suite =====\n")
    result = subprocess.run(["pytest"], check=False)
    return result.returncode


def run_standalone_tests():
    """
    Run standalone test scripts.
    
    Returns:
        bool: True if all standalone tests passed
    """
    print("\n===== Running standalone test scripts =====\n")
    
    # List of standalone test scripts
    standalone_scripts = [
        "test_placeholder.py",
        "test_status_tracking.py"
    ]
    
    tests_dir = Path(__file__).parent
    all_passed = True
    
    for script in standalone_scripts:
        script_path = tests_dir / script
        if script_path.exists():
            print(f"\nRunning {script}...")
            result = subprocess.run([sys.executable, script_path], check=False)
            if result.returncode != 0:
                all_passed = False
                print(f"❌ {script} FAILED with exit code {result.returncode}")
            else:
                print(f"✅ {script} PASSED")
        else:
            print(f"⚠️ {script} not found, skipping")
    
    return all_passed


def run_shell_tests():
    """
    Run shell-based integration tests.
    
    Returns:
        bool: True if all shell tests passed
    """
    print("\n===== Running shell integration tests =====\n")
    
    # List of shell test scripts
    shell_scripts = [
        "scripts/test_empty_run.sh",
        "scripts/test_with_files_run.sh"
    ]
    
    tests_dir = Path(__file__).parent
    all_passed = True
    
    for script in shell_scripts:
        script_path = tests_dir / script
        if script_path.exists():
            print(f"\nRunning {script}...")
            result = subprocess.run([str(script_path)], shell=True, check=False)
            if result.returncode != 0:
                all_passed = False
                print(f"❌ {script} FAILED with exit code {result.returncode}")
            else:
                print(f"✅ {script} PASSED")
        else:
            print(f"⚠️ {script} not found, skipping")
    
    return all_passed


def main():
    """
    Run all tests according to command line arguments.
    """
    parser = argparse.ArgumentParser(description="Run all tests for the transcribe project")
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument("--standalone-only", action="store_true", help="Run only standalone tests")
    parser.add_argument("--shell-only", action="store_true", help="Run only shell integration tests")
    
    args = parser.parse_args()
    
    # Determine what to run
    run_all = not (args.standalone_only or args.shell_only)
    run_standalone = run_all or args.standalone_only
    run_shell = run_all or args.shell_only
    
    if args.all:
        run_all = True
        run_standalone = True
        run_shell = True
    
    success = True
    
    # Run pytest if requested
    if run_all:
        pytest_result = run_pytest()
        if pytest_result != 0:
            success = False
    
    # Run standalone tests if requested
    if run_standalone:
        standalone_success = run_standalone_tests()
        if not standalone_success:
            success = False
    
    # Run shell tests if requested
    if run_shell:
        shell_success = run_shell_tests()
        if not shell_success:
            success = False
    
    # Print summary
    print("\n===== Test Summary =====")
    if success:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 