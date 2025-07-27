import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    VIDEODB_API_KEY = os.getenv("VIDEODB_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # RAG Configuration
    RAG_CONFIG = {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "embedding_model": "all-MiniLM-L6-v2",
        "top_k_results": 5,
        "similarity_threshold": 0.7
    }
    
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