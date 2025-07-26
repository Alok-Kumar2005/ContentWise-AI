from dataclasses import dataclass
from typing import List, Dict, Optional
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