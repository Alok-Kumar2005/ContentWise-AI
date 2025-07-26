import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    VIDEODB_API_KEY = os.getenv("VIDEODB_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Social Media Templates
    SOCIAL_MEDIA_TEMPLATES = {
        "linkedin": {
            "max_length": 3000,
            "tone": "professional",
            "hashtags": True
        },
        "twitter": {
            "max_length": 280,
            "tone": "casual",
            "hashtags": True
        },
        "instagram": {
            "max_length": 2200,
            "tone": "engaging",
            "hashtags": True
        },
        "facebook": {
            "max_length": 63206,
            "tone": "friendly",
            "hashtags": False
        }
    }
