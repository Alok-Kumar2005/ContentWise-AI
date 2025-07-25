import re
from typing import List, Dict, Any
import hashlib

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\"\']+', '', text)
    
    return text

def extract_timestamps(text: str) -> List[Dict[str, Any]]:
    """Extract timestamp information from text"""
    timestamp_pattern = r'(\d{1,2}):(\d{2}):(\d{2})'
    matches = re.finditer(timestamp_pattern, text)
    
    timestamps = []
    for match in matches:
        hours, minutes, seconds = map(int, match.groups())
        total_seconds = hours * 3600 + minutes * 60 + seconds
        timestamps.append({
            'time_str': match.group(),
            'seconds': total_seconds,
            'position': match.span()
        })
    
    return timestamps

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def generate_video_hash(content: str) -> str:
    """Generate a hash for video content for caching"""
    return hashlib.md5(content.encode()).hexdigest()

def format_duration(seconds: int) -> str:
    """Format duration in seconds to HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def validate_video_file(file_data: bytes, max_size_mb: int = 200) -> bool:
    """Validate uploaded video file"""
    # Check file size
    size_mb = len(file_data) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(f"File size ({size_mb:.1f}MB) exceeds limit ({max_size_mb}MB)")
    
    # Check if it's a video file (basic check)
    video_signatures = [
        b'\x00\x00\x00\x18ftypmp4',  # MP4
        b'\x00\x00\x00\x1cftypisom',  # MP4
        b'RIFF',  # AVI
        b'\x1aE\xdf\xa3',  # MKV
    ]
    
    for signature in video_signatures:
        if file_data.startswith(signature) or signature in file_data[:50]:
            return True
    
    # More lenient check for other formats
    return True

def extract_video_metadata(video_info: Dict) -> Dict[str, Any]:
    """Extract useful metadata from video info"""
    metadata = {
        'duration': video_info.get('duration', 0),
        'resolution': video_info.get('resolution', 'Unknown'),
        'format': video_info.get('format', 'Unknown'),
        'size_mb': video_info.get('size', 0) / (1024 * 1024) if video_info.get('size') else 0,
        'created_at': video_info.get('created_at', ''),
    }
    
    return metadata