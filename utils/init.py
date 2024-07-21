import streamlit as st
from streamlit.components.v1 import html
import os

def initialize():
    st.set_page_config(layout="wide", page_title="אפליקציה ההופכת קובץ PDF בעברית לקול ומחלצת גם את הטקסט", page_icon="🎙️")
    
    # Load external CSS
    css_file_path = os.path.join('utils', 'styles.css')
    with open(css_file_path, 'r') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    # # Load external JavaScript
    # js_file_path = os.path.join('utils', 'script.js')
    # with open(js_file_path, 'r') as f:
    #     st.markdown(f'<script>{f.read()}</script>', unsafe_allow_html=True)

    # Load header content
    header_file_path = os.path.join('utils', 'header.md')
    try:
        with open(header_file_path, 'r', encoding='utf-8') as header_file:
            header_content = header_file.read()
    except FileNotFoundError:
        st.error("header.md file not found in utils folder.")
        header_content = ""  # Provide a default empty header

    # Extract title and image path from header content
    header_lines = header_content.split('\n')
    title = header_lines[0].strip('# ')
    image_path = None    
    for line in header_lines:
        if line.startswith('!['):
            image_path = line.split('(')[1].split(')')[0]
            break
    
    # Load footer content
    footer_file_path = os.path.join('utils', 'footer.md')
    try:
        with open(footer_file_path, 'r', encoding='utf-8') as footer_file:
            footer_content = footer_file.read()
    except FileNotFoundError:
        st.error("footer.md file not found in utils folder.")
        footer_content = ""  # Provide a default empty footer    
    
    return title, image_path, footer_content