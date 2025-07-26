from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from config import Config
from models.video_processor import SocialMediaPost
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
            template="""
            Create a professional LinkedIn post based on this video content.
            
            Video Summary: {summary}
            Key Topics: {topics}
            Video URL: {video_url}
            
            Requirements:
            - Professional tone
            - Engaging opening hook
            - Key insights from the video
            - Call to action
            - Relevant hashtags (3-5)
            - Maximum {max_length} characters
            
            Make it valuable for professional network.
            """.replace("{max_length}", str(template["max_length"]))
        )
        
        return self._generate_post("linkedin", prompt, summary, key_topics, video_url)
    
    def generate_twitter_post(self, summary, key_topics, video_url=""):
        """Generate Twitter post"""
        template = Config.SOCIAL_MEDIA_TEMPLATES["twitter"]
        
        prompt = PromptTemplate(
            input_variables=["summary", "topics", "video_url"],
            template="""
            Create a Twitter thread (2-3 tweets) based on this video content.
            
            Video Summary: {summary}
            Key Topics: {topics}
            Video URL: {video_url}
            
            Requirements:
            - Casual, engaging tone
            - Hook in first tweet
            - Key insights in thread
            - Relevant hashtags (2-3 per tweet)
            - Each tweet max 280 characters
            
            Format as: Tweet 1/3: [content] \n Tweet 2/3: [content] etc.
            """.replace("{max_length}", str(template["max_length"]))
        )
        
        return self._generate_post("twitter", prompt, summary, key_topics, video_url)
    
    def generate_instagram_post(self, summary, key_topics, video_url=""):
        """Generate Instagram post"""
        template = Config.SOCIAL_MEDIA_TEMPLATES["instagram"]
        
        prompt = PromptTemplate(
            input_variables=["summary", "topics", "video_url"],
            template="""
            Create an Instagram post based on this video content.
            
            Video Summary: {summary}
            Key Topics: {topics}
            Video URL: {video_url}
            
            Requirements:
            - Engaging, visual storytelling tone
            - Compelling caption with emojis
            - Key insights from video
            - Story-like format
            - Relevant hashtags (5-10)
            - Maximum {max_length} characters
            
            Make it visually appealing and engaging.
            """.replace("{max_length}", str(template["max_length"]))
        )
        
        return self._generate_post("instagram", prompt, summary, key_topics, video_url)
    
    def generate_facebook_post(self, summary, key_topics, video_url=""):
        """Generate Facebook post"""
        template = Config.SOCIAL_MEDIA_TEMPLATES["facebook"]
        
        prompt = PromptTemplate(
            input_variables=["summary", "topics", "video_url"],
            template="""
            Create a Facebook post based on this video content.
            
            Video Summary: {summary}
            Key Topics: {topics}
            Video URL: {video_url}
            
            Requirements:
            - Friendly, conversational tone
            - Engaging story format
            - Key insights and takeaways
            - Questions to encourage engagement
            - Maximum {max_length} characters
            
            Make it shareable and discussion-worthy.
            """.replace("{max_length}", str(template["max_length"]))
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
            
            # Extract hashtags
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
