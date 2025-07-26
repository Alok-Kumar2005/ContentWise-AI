from pydantic import BaseModel
from typing import List, Dict

class SocialPosts(BaseModel):
    linkedin: str
    twitter: str
    facebook: str
    instagram: str

class Snippet(BaseModel):
    start: str
    end: str
    reason: str

class AnalysisResponse(BaseModel):
    summary: str
    key_quotes: List[str]
    topics: List[str]
    forecast: Dict[str, List[int]]  # e.g. {'timestamps': [...], 'counts': [...]}
    posts: SocialPosts
    snippets: List[Snippet]