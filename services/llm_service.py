from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from config import Config
from core.templates import Template
import logging

class LLMService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.7
        )
    
    def generate_summary(self, transcript, title=""):
        """Generate video summary from transcript"""
        prompt = PromptTemplate(
            input_variables=["transcript", "title"],
            template= Template.summary_template
        )
        
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(transcript=transcript, title=title)
            return response
        except Exception as e:
            logging.error(f"Error generating summary: {e}")
            return "Unable to generate summary"
    
    def extract_key_topics(self, transcript):
        """Extract key topics from transcript"""
        prompt = PromptTemplate(
            input_variables=["transcript"],
            template= Template.key_topic_template
        )
        
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(transcript=transcript)
            topics = [topic.strip() for topic in response.split(',')]
            return topics[:7]  # Limit to 7 topics
        except Exception as e:
            logging.error(f"Error extracting topics: {e}")
            return ["General Content"]