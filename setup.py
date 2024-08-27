from setuptools import setup, find_packages

setup(
    name='transcribe',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        # List your dependencies here
        'openai', 
        'assemblyai',
        'argparse', 
        'wave'
    ],
    entry_points={
        'console_scripts': [
            'transcribe=transcribe:main',  # Replace 'transcribe:main' with the path to your main function
        ],
    },
)