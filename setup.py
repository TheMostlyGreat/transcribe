"""
Setup script for the transcribe package.
"""

from setuptools import setup, find_packages
import os

# Manually define version instead of importing from package
__version__ = "0.1.0"

# Read the long description from the README file
if os.path.exists("README.md"):
    with open("README.md", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = ""

setup(
    name="transcribe",
    version=__version__,
    description="A simple media transcription tool using AssemblyAI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Alex Salazar",
    author_email="asalazar.personal@gmail.com",
    url="https://github.com/alex-salazar/transcribe",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "assemblyai>=0.5.0",
        "argparse>=1.4.0",
    ],
    entry_points={
        "console_scripts": [
            "transcribe=transcribe:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
    ],
)