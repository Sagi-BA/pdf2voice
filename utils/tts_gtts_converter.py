import os
import io
import uuid
import time
import asyncio
from gtts import gTTS
from gtts.lang import tts_langs
from gtts.tts import gTTSError
from aiohttp import ClientSession

class gTTSTextToSpeechConverter:
    def __init__(self, upload_dir="uploads"):
        self.UPLOAD_DIR = upload_dir
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        self.available_languages = tts_langs()
        self.session = None

    async def text_to_speech(self, text, language, max_retries=5, initial_delay=2, chunk_size=5000, status_callback=None):
        unique_filename = f"{uuid.uuid4()}.mp3"
        file_path = os.path.join(self.UPLOAD_DIR, unique_filename)

        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        combined_audio = io.BytesIO()
        
        start_time = time.time()

        self.session = ClientSession()
        try:
            for i, chunk in enumerate(chunks):
                if status_callback:
                    await status_callback(f"מעבד חלק {i+1} מתוך {len(chunks)}", (i + 1) / len(chunks))
                print(f"Processing chunk {i+1} of {len(chunks)}")
                await self._process_chunk(chunk, language, combined_audio, i, len(chunks), max_retries, initial_delay, status_callback)

            with open(file_path, 'wb') as f:
                f.write(combined_audio.getvalue())
        finally:
            await self.session.close()
            self.session = None

        end_time = time.time()
        total_time = end_time - start_time

        return file_path, total_time

    async def _process_chunk(self, chunk, language, combined_audio, chunk_num, total_chunks, max_retries, initial_delay, status_callback):
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                tts = gTTS(text=chunk, lang=language, slow=False)
                
                chunk_audio = io.BytesIO()
                await asyncio.get_event_loop().run_in_executor(None, tts.write_to_fp, chunk_audio)
                chunk_audio.seek(0)
                
                combined_audio.write(chunk_audio.getvalue())
                break
            except gTTSError as e:
                if "429" in str(e):
                    if status_callback:
                        await status_callback(f"הגבלת קצב API. מנסה שוב חלק {chunk_num + 1} בעוד {delay} שניות...", (chunk_num + 1) / total_chunks)
                    print(f"Rate limit hit. Retrying chunk {chunk_num + 1} in {delay} seconds...")
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    raise
            except Exception as e:
                if status_callback:
                    await status_callback(f"שגיאה בעיבוד חלק {chunk_num + 1}: {str(e)}", (chunk_num + 1) / total_chunks)
                print(f"Error processing chunk {chunk_num + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to convert chunk {chunk_num + 1} to speech after multiple retries")
                await asyncio.sleep(delay)
                delay *= 2

# Usage example
if __name__ == "__main__":
    converter = gTTSTextToSpeechConverter()
    
    text = "זוהי בדיקה של מערכת המרת טקסט לדיבור."
    language = "he"
    
    async def print_status(status, progress):
        print(f"{status} - Progress: {progress:.0%}")

    import asyncio
    file_path, total_time = asyncio.run(converter.text_to_speech(text, language, status_callback=print_status))
    print(f"Audio saved to: {file_path}")
    print(f"Conversion time: {total_time:.2f} seconds")
