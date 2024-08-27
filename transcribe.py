import os
import assemblyai as aai
import argparse

# Initialize AssemblyAI client with API key from environment variable
aai.settings.api_key = os.getenv('ASSEMBLY_API_KEY')

def transcribe_audio_file(audio_file_path):
    """
    Transcribe an audio file using AssemblyAI and save the transcription.

    Args:
        audio_file_path (str): Path to the audio file to transcribe.
    """
    transcriber = aai.Transcriber()
    config = aai.TranscriptionConfig(speaker_labels=True)

    transcript = transcriber.transcribe(
        audio_file_path,
        config=config
    )
    
    # Generate output file name by replacing audio extension with "_transcription.md"
    output_file_path = f"{os.path.splitext(audio_file_path)[0]}_transcription.md"
    
    # Save transcriptions to a markdown file
    with open(output_file_path, 'w') as output_file:
        for utterance in transcript.utterances:
            output_file.write(f"Speaker {utterance.speaker}: {utterance.text}\n")
    
    print(f"Transcription saved to {output_file_path}")

def main():
    """
    Parse command-line arguments and initiate audio transcription.
    """
    parser = argparse.ArgumentParser(description="Transcribe audio from an audio file.")
    parser.add_argument("audio_file_path", help="Path to the input audio file")
    args = parser.parse_args()

    transcribe_audio_file(args.audio_file_path)

if __name__ == "__main__":
    main()