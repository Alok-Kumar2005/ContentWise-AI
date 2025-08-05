from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime

@dataclass
class VideoAnalysis:
    video_id: str
    title: str
    description: str
    summary: str
    key_topics: List[str]
    transcript: str
    duration: float
    upload_timestamp: datetime
    
@dataclass
class SocialMediaPost:
    platform: str
    content: str
    hashtags: List[str]
    character_count: int
    
@dataclass
class TimestampQuery:
    query: str
    results: List[Dict]
    timestamps: List[tuple]

@dataclass
class QuizQuestion:
    question: str
    options: List[str] 
    correct_answer: int 
    explanation: str = ""

@dataclass
class Quiz:
    title: str
    questions: List[QuizQuestion]
    total_questions: int
    
    def __post_init__(self):
        self.total_questions = len(self.questions)