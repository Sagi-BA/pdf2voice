import streamlit as st
import asyncio
import PyPDF2
from gtts import gTTS
import os
import base64
from langdetect import detect
import uuid
import time
import requests  

from utils.init import initialize
from utils.counter import initialize_user_count, increment_user_count, decrement_user_count, get_user_count
from utils.TelegramSender import TelegramSender

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def detect_language(text):
    try:
        return detect(text)
    except:
        return 'en'  # default to English if detection fails

def text_to_speech(text, language, max_retries=5, delay=2):
    if language == 'he':
        language = 'iw'  # gTTS uses 'iw' for Hebrew
    unique_filename = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    for attempt in range(max_retries):
        try:
            tts = gTTS(text=text, lang=language, slow=False)
            tts.save(file_path)
            return file_path
        except requests.exceptions.RequestException as e:
            if e.response.status_code == 429:
                # If we hit the rate limit, wait and retry
                print(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                # For other types of request exceptions, re-raise the exception
                raise
        except Exception as e:
            # Handle other exceptions (like network errors)
            print(f"An error occurred: {e}")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    raise Exception("Failed to convert text to speech after multiple retries")

def get_binary_file_downloader_html(bin_file, file_label='קובץ'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'data:application/octet-stream;base64,{bin_str}'
    custom_css = f"""
        <style>
            .download-button {{
                width: 100%;
                margin: 0.5rem 0;
                background-color: #ff0000;  /* אדום */
                color: white !important;  /* לבן עם !important כדי לוודא שהצבע יחול */
                font-weight: bold;
                border: 2px solid #ff0000;
                border-radius: 10px;
                padding: 12px 24px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 24px;
                cursor: pointer;
                transition: background-color 0.3s, border-color 0.3s;
                
            }}
            .download-button:hover {{
                background-color: #cc0000;  /* אדום כהה יותר */
                border-color: #cc0000;
                color: white !important;  /* לוודא שהצבע נשאר לבן גם ב-hover */
            }}
            @media screen and (max-width: 768px) {{
                .download-button {{
                    padding: 10px 20px;
                    font-size: 16px;
                }}
            }}
            @media screen and (max-width: 480px) {{
                .download-button {{
                    padding: 8px 16px;
                    font-size: 14px;
                }}
            }}
        </style>
    """
    download_button = f'<a href="{href}" download="{os.path.basename(bin_file)}" class="download-button">לחיצה להורדת {file_label}</a>'
    return f'{custom_css}{download_button}'

# Initialize TelegramSender
if 'telegram_sender' not in st.session_state:
    st.session_state.telegram_sender = TelegramSender()

# Increment user count if this is a new session
if 'counted' not in st.session_state:
    st.session_state.counted = True
    increment_user_count()

# Initialize user count
initialize_user_count()

def main():
    try:
        header_content, image_path, footer_content = initialize()

        st.markdown(f"<h2 style='text-align: center; color: #FF6347;'>{header_content}</h2>", unsafe_allow_html=True)

        if image_path:
            st.image(image_path, use_column_width=True)

        st.info("אפליקציה זו משתמשת בזיהוי שפות אוטומטי ותומכת במספר שפות, כולל עברית.")

         # הוספת הערה לגבי מגבלת גודל הקובץ
        st.warning("שימו לב: ניתן להעלות קבצי PDF בגודל של עד 2 מגה-בייט.")

        uploaded_file = st.file_uploader("יש לבחור קובץ PDF", type="pdf")

        if uploaded_file is not None:
            original_filename = uploaded_file.name  # Store the original filename
            # Check file size
            if uploaded_file.size > 2 * 1024 * 1024:  # 2 MB in bytes
                st.error("גודל הקובץ חורג מהמגבלה של 2 מגה-בייט. אנא העלה קובץ קטן יותר.")
            else:
                if st.button("חלץ קול וטקסט"):
                    # Extract text from PDF
                    text = extract_text_from_pdf(uploaded_file)
                    
                    # Display extracted text with custom styling
                    st.markdown("<p class='extracted-text-header'>טקסט שחולץ</p>", unsafe_allow_html=True)
                    st.text_area("", text, height=300, key="extracted_text")
                    
                    # Detect language
                    detected_lang = detect_language(text)
                    st.info(f"שפה שזוהתה: {detected_lang}")
                    
                    # Convert text to speech with a spinner
                    with st.spinner("ממיר טקסט לדיבור... זה עשוי לקחת מספר רגעים."):
                        audio_file_path = text_to_speech(text, detected_lang)
                    
                    # Provide download link for MP3
                    st.success("ההמרה הושלמה!")
                    st.subheader("האזנה לאודיו")
                    
                    # Display audio player
                    with open(audio_file_path, 'rb') as audio_file:
                        audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format='audio/mp3')
                    
                    st.subheader("הורד MP3")
                    st.markdown(get_binary_file_downloader_html(audio_file_path, 'אודיו'), unsafe_allow_html=True)
                    
                    # שליחה לטלגרם
                    asyncio.run(send_telegram_message_and_file(
                        f"PDF2VOICE: {os.path.basename(original_filename)}",
                        audio_file_path
                    ))
                    
                    # Delete the file after sending
                    os.remove(audio_file_path)
    
    except Exception as e:
        st.error(f"אירעה שגיאה בעת עיבוד הקובץ: {str(e)}")
    
    user_count = get_user_count(formatted=True)
    footer_with_count = f"{footer_content}\n\n<p class='user-count' style='color: #4B0082;'>סה\"כ משתמשים: {user_count}</p>"
    st.markdown(footer_with_count, unsafe_allow_html=True)
    
async def send_telegram_message_and_file(message, file_path):
    sender = st.session_state.telegram_sender
    try:
        await sender.send_document(file_path, message)
    finally:
        await sender.close_session()

if __name__ == "__main__":
    main()
