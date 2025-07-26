import os
import tempfile
import requests
from datetime import datetime

def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary location"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name

def validate_video_url(url):
    """Validate if URL is a valid video URL"""
    valid_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com']
    return any(domain in url.lower() for domain in valid_domains)

def format_timestamp(seconds):
    """Format seconds to MM:SS or HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"