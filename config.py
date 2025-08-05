import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    VIDEODB_API_KEY = os.getenv("VIDEODB_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Social Media Templates Configuration
    SOCIAL_MEDIA_TEMPLATES = {
        "linkedin": {
            "max_length": 3000,
            "hashtag_count": 5,
            "tone": "professional"
        },
        "twitter": {
            "max_length": 280,
            "hashtag_count": 3,
            "tone": "casual"
        },
        "instagram": {
            "max_length": 2200,
            "hashtag_count": 8,
            "tone": "visual"
        },
        "facebook": {
            "max_length": 63206,
            "hashtag_count": 4,
            "tone": "conversational"
        }
    }
    
    # Quiz Configuration
    QUIZ_CONFIG = {
        "default_questions": 5,
        "max_questions": 10,
        "min_questions": 3,
        "passing_grade": 60,  # Percentage
        "max_transcript_length": 8000,  # Characters for LLM processing
        "question_types": [
            "factual_recall",
            "conceptual_understanding", 
            "application",
            "analysis"
        ],
        "difficulty_levels": {
            "easy": 0.4,    # 40% easy questions
            "medium": 0.4,  # 40% medium questions  
            "hard": 0.2     # 20% hard questions
        }
    }
    
    # RAG Configuration
    RAG_CONFIG = {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "temperature": 0.7,
        "max_tokens": 500,
        "retrieval_count": 5
    }
    
    # File Upload Configuration
    UPLOAD_CONFIG = {
        "max_file_size": 500,  # MB
        "allowed_extensions": ['mp4', 'avi', 'mov', 'mkv', 'webm', 'm4v', 'flv'],
        "temp_directory": "temp_uploads"
    }
    
    # Logging Configuration
    LOGGING_CONFIG = {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": "video_analysis.log"
    }
    
    @classmethod
    def validate_config(cls):
        """Validate that required configuration is present"""
        errors = []
        
        if not cls.VIDEODB_API_KEY:
            errors.append("VIDEODB_API_KEY environment variable is required")
        
        if not cls.GOOGLE_API_KEY:
            errors.append("GOOGLE_API_KEY environment variable is required")
        
        if errors:
            raise ValueError("Configuration errors: " + ", ".join(errors))
        
        return True
    
    @classmethod
    def get_quiz_settings(cls):
        """Get quiz-specific settings"""
        return cls.QUIZ_CONFIG
    
    @classmethod
    def get_social_media_template(cls, platform):
        """Get social media template for specific platform"""
        return cls.SOCIAL_MEDIA_TEMPLATES.get(platform.lower(), cls.SOCIAL_MEDIA_TEMPLATES["linkedin"])