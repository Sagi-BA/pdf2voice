import pyttsx3
import os
import uuid
import time
import asyncio
import streamlit as st

class Pyttsx3TextToSpeechConverter:
    def __init__(self, upload_dir="uploads"):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[1].id)
        
        self.UPLOAD_DIR = upload_dir
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        
    async def text_to_speech(self, text, language, chunk_size=1000, status_callback=None):
        unique_filename = f"{uuid.uuid4()}.mp3"
        file_path = os.path.join(self.UPLOAD_DIR, unique_filename)

        # Split the text into chunks
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        start_time = time.time()

        temp_files = []
        temp_filename = f"{uuid.uuid4()}_chunk"
        for i, chunk in enumerate(chunks):
            if status_callback:
                await status_callback(f"Processing chunk {i+1} of {len(chunks)}", (i + 1) / len(chunks))
            progress_bar.progress((i + 1) / len(chunks))
            
            # Create a temporary file for each chunk with a unique name
            temp_filename = f"{temp_filename}_{i}.mp3"
            temp_filepath = os.path.join(self.UPLOAD_DIR, temp_filename)
            temp_files.append(temp_filepath)
            
            self.engine.save_to_file(chunk, temp_filepath)
            self.engine.runAndWait()

        # Combine all temporary files
        with open(file_path, 'wb') as outfile:
            for temp_file in temp_files:
                with open(temp_file, 'rb') as infile:
                    outfile.write(infile.read())
                os.remove(temp_file)  # Remove temporary file

        end_time = time.time()
        total_time = end_time - start_time
        
        progress_bar.empty()

        return file_path, total_time
    
    async def print_available_voices(self):
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')

        print("Available voices:")
        for i, voice in enumerate(voices):
            print(f"{i+1}. ID: {voice.id}")
            print(f"   Name: {voice.name}")
            print(f"   Languages: {voice.languages}")
            print(f"   Gender: {voice.gender}")
            print(f"   Age: {voice.age}")
            print("--------------------")

# Usage example (can be commented out or removed if you're importing this class elsewhere)
if __name__ == "__main__":
    converter = Pyttsx3TextToSpeechConverter()
    
    text = "This is a test of the text-to-speech conversion system." * 1000  # Long text
    language = "en"
    
    async def print_status(status, progress):
        print(f"{status} - Progress: {progress:.0%}")

    async def main():
        file_path, total_time = await converter.text_to_speech(text, language, status_callback=print_status)
        print(f"Audio saved to: {file_path}")
        print(f"Conversion time: {total_time:.2f} seconds")

    asyncio.run(main())