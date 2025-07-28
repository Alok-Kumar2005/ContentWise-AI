from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from config import Config
from models.video_processor import SocialMediaPost
from core.templates import Template
import logging

class SocialMediaGenerator:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.8
        )
    
    def generate_linkedin_post(self, summary, key_topics, video_url=""):
        """Generate LinkedIn post"""
        template = Config.SOCIAL_MEDIA_TEMPLATES["linkedin"]
        
        prompt = PromptTemplate(
            input_variables=["summary", "topics", "video_url"],
            template=Template.linkedin_template.replace("{max_length}", str(template["max_length"]))
        )
        
        return self._generate_post("linkedin", prompt, summary, key_topics, video_url)
    
    def generate_twitter_post(self, summary, key_topics, video_url=""):
        """Generate Twitter post"""
        template = Config.SOCIAL_MEDIA_TEMPLATES["twitter"]
        
        prompt = PromptTemplate(
            input_variables=["summary", "topics", "video_url"],
            template=Template.twitter_template.replace("{max_length}", str(template["max_length"]))
        )
        
        return self._generate_post("twitter", prompt, summary, key_topics, video_url)
    
    def generate_instagram_post(self, summary, key_topics, video_url=""):
        """Generate Instagram post"""
        template = Config.SOCIAL_MEDIA_TEMPLATES["instagram"]
        
        prompt = PromptTemplate(
            input_variables=["summary", "topics", "video_url"],
            template= Template.instagram_template.replace("{max_length}", str(template["max_length"]))
        )
        
        return self._generate_post("instagram", prompt, summary, key_topics, video_url)
    
    def generate_facebook_post(self, summary, key_topics, video_url=""):
        """Generate Facebook post"""
        template = Config.SOCIAL_MEDIA_TEMPLATES["facebook"]
        
        prompt = PromptTemplate(
            input_variables=["summary", "topics", "video_url"],
            template= Template.facebook_template.replace("{max_length}", str(template["max_length"]))
        )
        
        return self._generate_post("facebook", prompt, summary, key_topics, video_url)
    
    def _generate_post(self, platform, prompt, summary, topics, video_url):
        """Generate social media post using LLM"""
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt)
            content = chain.run(
                summary=summary,
                topics=", ".join(topics),
                video_url=video_url
            )
            
            hashtags = self._extract_hashtags(content)
            
            return SocialMediaPost(
                platform=platform,
                content=content,
                hashtags=hashtags,
                character_count=len(content)
            )
        except Exception as e:
            logging.error(f"Error generating {platform} post: {e}")
            return SocialMediaPost(
                platform=platform,
                content=f"Unable to generate {platform} post",
                hashtags=[],
                character_count=0
            )
    
    def _extract_hashtags(self, content):
        """Extract hashtags from content"""
        import re
        hashtags = re.findall(r'#\w+', content)
        return hashtags
