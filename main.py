import asyncio
import base64
import os
import functools
from functools import lru_cache

import PyPDF2
import streamlit as st
from langdetect import detect

from utils.init import initialize
from utils.counter import initialize_user_count, increment_user_count, get_user_count
from utils.TelegramSender import TelegramSender
from utils.tts_pyttsx3_converter import Pyttsx3TextToSpeechConverter
from utils.tts_gtts_converter import gTTSTextToSpeechConverter

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def clean_text(input_text):
    # Split the text into lines
    lines = input_text.split('\n')
    
    # Process each line
    cleaned_lines = []
    for line in lines:
        # Remove spaces between characters and strip leading/trailing spaces
        cleaned_line = ''.join(line.split()).strip()
        if cleaned_line:  # Only add non-empty lines
            cleaned_lines.append(cleaned_line)
    
    # Join the cleaned lines back together
    return ' '.join(cleaned_lines)

def async_lru_cache(maxsize=128, typed=False):
    def decorator(func):
        sync_func = functools.lru_cache(maxsize=maxsize, typed=typed)(func)
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await sync_func(*args, **kwargs)
        return wrapper
    return decorator

@async_lru_cache(maxsize=100)
async def cached_text_to_speech(text, language):
    progress_bar = st.progress(0)
    status_text = st.empty()

    async def update_status(status, progress):
        status_text.text(status)
        progress_bar.progress(progress)

    if language == 'he' or language == 'iw':
        print("text_to_speech: language=hebrew")
        language = 'iw'  # gTTS uses 'iw' for Hebrew
        converter = gTTSTextToSpeechConverter()   
    else:
        print(f"text_to_speech: language={language}")
        if not language.startswith('en'):
            text=clean_text(text)
        
        converter = Pyttsx3TextToSpeechConverter()

    result = await converter.text_to_speech(text, language, status_callback=update_status)
    
    progress_bar.empty()
    status_text.empty()
    
    return result

async def extract_text_from_pdf(file):
    text = ""
    pdf_reader = PyPDF2.PdfReader(file)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def detect_language(text):
    try:
        return detect(text)
    except:
        return 'en'

def get_binary_file_downloader_html(bin_file, file_label='קובץ'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'data:application/octet-stream;base64,{bin_str}'
    return f'<a href="{href}" download="{os.path.basename(bin_file)}" class="download-button">לחיצה להורדת {file_label}</a>'

def format_conversion_time(total_seconds):
    minutes, seconds = divmod(int(total_seconds), 60)
    if minutes > 0:
        return f"{minutes} דקות ו-{seconds} שניות" if seconds > 0 else f"{minutes} דקות"
    return f"{seconds} שניות"


async def process_file(file, original_filename):
    text = await extract_text_from_pdf(file)
    st.text_area("טקסט שחולץ", text, height=300, key="extracted_text")
    
    detected_lang = detect_language(text)
    st.info(f"שפה שזוהתה: {detected_lang}")
    
    with st.spinner("ממיר טקסט לדיבור... זה עשוי לקחת מספר רגעים."):
        audio_file_path, conversion_time = await cached_text_to_speech(text, detected_lang)
        formatted_time = format_conversion_time(conversion_time)
        st.success(f"ההמרה הושלמה ב-{formatted_time}")
    
    try:
        with open(audio_file_path, 'rb') as audio_file:
            st.audio(audio_file.read(), format='audio/mp3')
        
        st.markdown(get_binary_file_downloader_html(audio_file_path, 'אודיו'), unsafe_allow_html=True)
        
        await send_telegram_message_and_file(f"PDF2VOICE: {original_filename}", audio_file_path)
    finally:
        # Delete the file after sending and displaying
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
            print(f"Deleted temporary file: {audio_file_path}")

async def send_telegram_message_and_file(message, file_path):
    sender = st.session_state.telegram_sender
    try:
        await sender.send_document(file_path, message)
    finally:
        await sender.close_session()

import subprocess
import sys


def install_dependencies():
    try:
        # Run the command to install libespeak1
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyttsx3'])
        subprocess.check_call(['sudo', 'apt-get', 'update'])
        subprocess.check_call(['sudo', 'apt-get', 'install', '-y', 'libespeak1'])
        st.success("Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        st.error(f"An error occurred: {e}")

st.title("Install Dependencies")

if st.button("Install libespeak1"):
    install_dependencies()

async def main():
    try:
        header_content, image_path, footer_content = initialize()
        
        st.markdown(f"<h2 style='text-align: center; color: #FF6347;'>{header_content}</h2>", unsafe_allow_html=True)
        if image_path:
            st.image(image_path, use_column_width=True)

        st.info("אפליקציה זו משתמשת בזיהוי שפות אוטומטי ותומכת במספר שפות, כולל עברית.")
        st.warning("שימו לב: ניתן להעלות קבצי PDF בגודל של עד 2 מגה-בייט.")

        uploaded_file = st.file_uploader("יש לבחור קובץ PDF", type="pdf")

        if uploaded_file is not None:
            if uploaded_file.size > 2 * 1024 * 1024:
                st.error("גודל הקובץ חורג מהמגבלה של 2 מגה-בייט. אנא העלה קובץ קטן יותר.")
            elif st.button("חלץ קול וטקסט"):
                await process_file(uploaded_file, uploaded_file.name)

    except Exception as e:
        st.error(f"אירעה שגיאה בעת עיבוד הקובץ: {str(e)}")
    
    user_count = get_user_count(formatted=True)
    footer_with_count = f"{footer_content}\n\n<p class='user-count' style='color: #4B0082;'>סה\"כ משתמשים: {user_count}</p>"
    st.markdown(footer_with_count, unsafe_allow_html=True)

if __name__ == "__main__":
    if 'telegram_sender' not in st.session_state:
        st.session_state.telegram_sender = TelegramSender()
    if 'counted' not in st.session_state:
        st.session_state.counted = True
        increment_user_count()
    initialize_user_count()
    asyncio.run(main())
