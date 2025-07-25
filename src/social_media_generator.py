from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import Dict, Any
from src.utils.config import Config

class SocialMediaGenerator:
    def __init__(self):
        self.llm = None
        self.initialize_llm()
    
    def initialize_llm(self):
        """Initialize LangChain LLM"""
        try:
            if Config.GOOGLE_API_KEY:
                self.llm = ChatGoogleGenerativeAI(model = "gemini-1.5-flash" , google_api_key = Config.GOOGLE_API_KEY )
        except Exception as e:
            print(f"Error initializing LLM: {e}")
    
    def generate_posts(self, video_analysis: Dict[str, Any]) -> Dict[str, str]:
        """Generate social media posts for all platforms"""
        if not self.llm:
            raise Exception("LLM not properly initialized. Check OpenAI API key.")
        
        posts = {}
        
        # Generate posts for each platform
        platforms = {
            'facebook': self._generate_facebook_post,
            'twitter': self._generate_twitter_post,
            'linkedin': self._generate_linkedin_post,
            'instagram': self._generate_instagram_post
        }
        
        for platform, generator_func in platforms.items():
            try:
                posts[platform] = generator_func(video_analysis)
            except Exception as e:
                posts[platform] = f"Error generating {platform} post: {str(e)}"
        
        return posts
    
    def _generate_facebook_post(self, analysis: Dict[str, Any]) -> str:
        """Generate Facebook post"""
        prompt = PromptTemplate(
            input_variables=["summary", "topics", "quotes"],
            template="""
            Create an engaging Facebook post based on this video analysis:
            
            Summary: {summary}
            Topics: {topics}
            Key Quotes: {quotes}
            
            Requirements:
            - Conversational and engaging tone
            - Include relevant emojis
            - Ask a question to encourage engagement
            - Include relevant hashtags
            - Length: 100-200 words
            
            Facebook Post:
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        return chain.run(
            summary=analysis.get('summary', ''),
            topics=', '.join(analysis.get('topics', [])),
            quotes=', '.join(analysis.get('key_quotes', [])[:2])
        )
    
    def _generate_twitter_post(self, analysis: Dict[str, Any]) -> str:
        """Generate Twitter post"""
        prompt = PromptTemplate(
            input_variables=["summary", "topics"],
            template="""
            Create a compelling Twitter thread (2-3 tweets) based on this video analysis:
            
            Summary: {summary}
            Topics: {topics}
            
            Requirements:
            - Each tweet max 280 characters
            - Include relevant emojis and hashtags
            - Make it shareable and engaging
            - Use thread format (1/3, 2/3, 3/3)
            
            Twitter Thread:
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        return chain.run(
            summary=analysis.get('summary', ''),
            topics=', '.join(analysis.get('topics', []))
        )
    
    def _generate_linkedin_post(self, analysis: Dict[str, Any]) -> str:
        """Generate LinkedIn post"""
        prompt = PromptTemplate(
            input_variables=["summary", "topics", "quotes"],
            template="""
            Create a professional LinkedIn post based on this video analysis:
            
            Summary: {summary}
            Topics: {topics}
            Key Quotes: {quotes}
            
            Requirements:
            - Professional and insightful tone
            - Include key learnings or takeaways
            - Add relevant industry hashtags
            - Encourage professional discussion
            - Length: 150-300 words
            
            LinkedIn Post:
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        return chain.run(
            summary=analysis.get('summary', ''),
            topics=', '.join(analysis.get('topics', [])),
            quotes=', '.join(analysis.get('key_quotes', [])[:2])
        )
    
    def _generate_instagram_post(self, analysis: Dict[str, Any]) -> str:
        """Generate Instagram post"""
        prompt = PromptTemplate(
            input_variables=["summary", "topics"],
            template="""
            Create a visually-focused Instagram post based on this video analysis:
            
            Summary: {summary}
            Topics: {topics}
            
            Requirements:
            - Visual and aesthetic focus
            - Include relevant emojis throughout
            - Suggest photo/video ideas in [brackets]
            - Use trending hashtags
            - Engaging and inspirational tone
            - Length: 100-150 words
            
            Instagram Post:
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        return chain.run(
            summary=analysis.get('summary', ''),
            topics=', '.join(analysis.get('topics', []))
        )
    
    def customize_post(self, platform: str, original_post: str, customization_request: str) -> str:
        """Customize an existing post based on user request"""
        prompt = PromptTemplate(
            input_variables=["platform", "original_post", "request"],
            template="""
            Modify the following {platform} post based on the user's request:
            
            Original Post: {original_post}
            User Request: {request}
            
            Please provide the modified post while maintaining the platform's best practices.
            
            Modified Post:
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        return chain.run(
            platform=platform,
            original_post=original_post,
            request=customization_request
        )