import videodb
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import Dict, List, Optional, Any
import tempfile
import os
from src.utils.config import Config

class VideoProcessor:
    def __init__(self):
        self.videodb_client = None
        self.llm = None
        self.initialize_clients()
    
    def initialize_clients(self):
        """Initialize VideoDB and LangChain clients"""
        try:
            if Config.VIDEODB_API_KEY:
                # Initialize VideoDB
                videodb.connect(api_key=Config.VIDEODB_API_KEY)
                self.videodb_client = videodb
            
            if Config.GOOGLE_API_KEY:
                # Initialize LangChain LLM
                self.llm = ChatGoogleGenerativeAI(model = "gemini-1.5-flash" , google_api_key = Config.GOOGLE_API_KEY )
        except Exception as e:
            print(f"Error initializing clients: {e}")
    
    def process_video(self, uploaded_file=None, video_url=None, title="", description="") -> Dict[str, Any]:
        """Process video and extract analysis"""
        if not self.videodb_client or not self.llm:
            raise Exception("Clients not properly initialized. Check API keys.")
        
        try:
            # Upload video to VideoDB
            if uploaded_file:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    video_path = tmp_file.name
                
                # Upload to VideoDB
                video = self.videodb_client.upload(path=video_path)
                os.unlink(video_path)  # Clean up temp file
                
            elif video_url:
                # Upload from URL
                video = self.videodb_client.upload(url=video_url)
            else:
                raise ValueError("Either uploaded_file or video_url must be provided")
            
            # Get video transcript
            transcript = video.get_transcript()
            
            # Generate analysis using LangChain
            analysis = self._analyze_content(transcript, title, description)
            analysis['video_id'] = video.id
            analysis['video'] = video
            
            return analysis
            
        except Exception as e:
            raise Exception(f"Error processing video: {str(e)}")
    
    def _analyze_content(self, transcript: str, title: str, description: str) -> Dict[str, Any]:
        """Analyze video content using LangChain"""
        
        # Summary generation
        summary_prompt = PromptTemplate(
            input_variables=["transcript", "title", "description"],
            template="""
            Analyze the following video content and provide a comprehensive summary.
            
            Title: {title}
            Description: {description}
            Transcript: {transcript}
            
            Please provide:
            1. A concise summary (2-3 sentences)
            2. Key topics discussed (3-5 topics)
            3. Important quotes or statements (3-5 quotes)
            
            Format your response as:
            SUMMARY: [your summary here]
            TOPICS: [topic1, topic2, topic3, ...]
            QUOTES: [quote1 | quote2 | quote3 | ...]
            """
        )
        
        summary_chain = LLMChain(llm=self.llm, prompt=summary_prompt)
        result = summary_chain.run(
            transcript=transcript[:4000],  # Limit transcript length
            title=title or "Untitled Video",
            description=description or "No description provided"
        )
        
        # Parse the result
        analysis = self._parse_analysis_result(result)
        return analysis
    
    def _parse_analysis_result(self, result: str) -> Dict[str, Any]:
        """Parse the LLM analysis result"""
        analysis = {
            'summary': '',
            'topics': [],
            'key_quotes': []
        }
        
        lines = result.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('SUMMARY:'):
                analysis['summary'] = line.replace('SUMMARY:', '').strip()
            elif line.startswith('TOPICS:'):
                topics_str = line.replace('TOPICS:', '').strip()
                analysis['topics'] = [topic.strip() for topic in topics_str.split(',') if topic.strip()]
            elif line.startswith('QUOTES:'):
                quotes_str = line.replace('QUOTES:', '').strip()
                analysis['key_quotes'] = [quote.strip() for quote in quotes_str.split('|') if quote.strip()]
        
        return analysis
    
    def query_video(self, query: str, video_id: str) -> Dict[str, Any]:
        """Query specific information from the video"""
        try:
            # Get video object
            video = self.videodb_client.get_video(video_id)
            
            # Search in video using VideoDB's search functionality
            search_results = video.search(query)
            
            # Generate response using LangChain
            response_prompt = PromptTemplate(
                input_variables=["query", "search_results"],
                template="""
                Based on the following search results from a video, answer the user's question.
                
                Question: {query}
                Search Results: {search_results}
                
                Provide a clear and concise answer based on the search results.
                If timestamps are available, include them in your response.
                """
            )
            
            response_chain = LLMChain(llm=self.llm, prompt=response_prompt)
            response = response_chain.run(
                query=query,
                search_results=str(search_results)
            )
            
            # Extract timestamps from search results
            timestamps = []
            if hasattr(search_results, 'shots'):
                for shot in search_results.shots[:5]:  # Limit to top 5 results
                    timestamps.append({
                        'start': shot.start,
                        'end': shot.end,
                        'content': shot.text
                    })
            
            return {
                'response': response,
                'timestamps': timestamps,
                'search_results': search_results
            }
            
        except Exception as e:
            raise Exception(f"Error querying video: {str(e)}")
    
    def create_compilation(self, video_id: str, criteria: str, max_duration: int = 180) -> str:
        """Create video compilation based on criteria"""
        try:
            video = self.videodb_client.get_video(video_id)
            
            # Search for relevant segments
            search_results = video.search(criteria)
            
            # Create compilation using VideoDB
            timeline = videodb.Timeline()
            
            total_duration = 0
            for shot in search_results.shots:
                if total_duration + (shot.end - shot.start) <= max_duration:
                    timeline.add_inline(shot)
                    total_duration += (shot.end - shot.start)
                else:
                    break
            
            # Generate compilation
            compilation = timeline.generate()
            return compilation.stream_url
            
        except Exception as e:
            raise Exception(f"Error creating compilation: {str(e)}")