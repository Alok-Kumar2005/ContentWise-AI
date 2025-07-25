import os
from dataclasses import dataclass

@dataclass
class Config:
    """Configuration class for API keys and settings"""
    VIDEODB_API_KEY: str = os.getenv("VIDEODB_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    MAX_TRANSCRIPT_LENGTH: int = 5000
    MAX_VIDEO_SIZE_MB: int = 200
    
    # Social media platform limits
    TWITTER_CHAR_LIMIT: int = 280
    FACEBOOK_WORD_LIMIT: int = 200
    LINKEDIN_WORD_LIMIT: int = 300
    INSTAGRAM_WORD_LIMIT: int = 150