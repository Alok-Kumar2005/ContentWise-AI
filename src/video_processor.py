from videodb import connect
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import Dict, List, Optional, Any
import tempfile
import os
from src.utils.config import Config

class VideoProcessor:
    def __init__(self):
        self.conn = None
        self.llm = None
        self.initialize_clients()
    
    def _wait_for_transcript(self, video, max_wait_time=300, check_interval=10):
        """Wait for transcript generation to complete"""
        import time
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                # Try to get transcript status or just try to get it
                transcript = video.get_transcript()
                if transcript:
                    return transcript
            except Exception as e:
                error_msg = str(e).lower()
                if "does not exist" in error_msg or "not found" in error_msg:
                    print(f"Transcript not ready yet, waiting {check_interval} seconds...")
                    time.sleep(check_interval)
                    continue
                else:
                    # Some other error, re-raise it
                    raise e
        
        raise Exception(f"Transcript generation timed out after {max_wait_time} seconds")
    
    def initialize_clients(self):
        """Initialize VideoDB and LangChain clients"""
        try:
            if Config.VIDEODB_API_KEY:
                # Initialize VideoDB connection
                self.conn = connect(api_key=Config.VIDEODB_API_KEY)
            
            if Config.GOOGLE_API_KEY:
                # Initialize LangChain LLM
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash", 
                    google_api_key=Config.GOOGLE_API_KEY
                )
        except Exception as e:
            print(f"Error initializing clients: {e}")
    
    def process_video(self, uploaded_file=None, video_url=None, title="", description="") -> Dict[str, Any]:
        """Process video and extract analysis"""
        if not self.conn or not self.llm:
            raise Exception("Clients not properly initialized. Check API keys.")
        
        try:
            # Upload video to VideoDB
            if uploaded_file:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    video_path = tmp_file.name
                
                # Upload to VideoDB using connection
                video = self.conn.upload(path=video_path)
                os.unlink(video_path)  # Clean up temp file
                
            elif video_url:
                # Upload from URL using connection
                video = self.conn.upload(url=video_url)
            else:
                raise ValueError("Either uploaded_file or video_url must be provided")
            
            # Generate stream for the video
            video.generate_stream()
            
            # Generate and get video transcript
            transcript_text = ""
            try:
                print("Generating transcript...")
                # First, generate the transcript
                video.generate_transcript()
                
                print("Waiting for transcript to be ready...")
                # Wait for transcript to be generated and then get it
                transcript = self._wait_for_transcript(video, max_wait_time=180)
                
                if hasattr(transcript, 'text'):
                    transcript_text = transcript.text
                elif isinstance(transcript, str):
                    transcript_text = transcript
                elif hasattr(transcript, 'content'):
                    transcript_text = transcript.content
                elif hasattr(transcript, 'data'):
                    transcript_text = transcript.data
                else:
                    transcript_text = str(transcript)
                    
                print(f"Transcript retrieved successfully, length: {len(transcript_text)}")
                    
            except Exception as e:
                print(f"Error with transcript: {e}")
                # Fallback to scene indexing for content analysis
                try:
                    print("Falling back to scene indexing...")
                    index_id = video.index_scenes(
                        prompt="Describe what is being discussed or shown in this scene in detail, including any dialogue or narration"
                    )
                    print(f"Scene indexing started with ID: {index_id}")
                    # For now, we'll use a placeholder text and rely on search functionality
                    transcript_text = "Video has been indexed for scene-based analysis. Use the search feature to query specific content."
                    
                except Exception as idx_error:
                    print(f"Error with scene indexing: {idx_error}")
                    # Final fallback - basic video info
                    transcript_text = "Video uploaded successfully. Analysis capabilities may be limited without transcript or scene indexing."
            
            # Generate analysis using LangChain
            analysis = self._analyze_content(transcript_text, title, description)
            analysis['video_id'] = video.id
            analysis['video_object'] = video
            
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
            Content: {transcript}
            
            Please provide:
            1. A concise summary (2-3 sentences)
            2. Key topics discussed (3-5 topics)
            3. Important themes or points (3-5 points)
            
            Format your response as:
            SUMMARY: [your summary here]
            TOPICS: [topic1, topic2, topic3, ...]
            QUOTES: [point1 | point2 | point3 | ...]
            """
        )
        
        summary_chain = LLMChain(llm=self.llm, prompt=summary_prompt)
        result = summary_chain.run(
            transcript=transcript[:4000] if transcript else "Content analysis pending",
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
        
        # Fallback parsing if format is different
        if not analysis['summary'] and result:
            analysis['summary'] = result[:200] + "..." if len(result) > 200 else result
        
        return analysis
    
    def query_video(self, query: str, video_id: str) -> Dict[str, Any]:
        """Query specific information from the video"""
        try:
            # Get video object from stored reference or recreate
            if hasattr(self, '_current_video') and self._current_video.id == video_id:
                video = self._current_video
            else:
                # Note: VideoDB might not have a direct get_video method
                # You might need to store video objects or use a different approach
                raise Exception("Video object not found. Please re-upload the video.")
            
            # Search in video using VideoDB's search functionality
            try:
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
                            'content': getattr(shot, 'text', 'Content found')
                        })
                elif hasattr(search_results, 'results'):
                    for result in search_results.results[:5]:
                        timestamps.append({
                            'start': getattr(result, 'start', 0),
                            'end': getattr(result, 'end', 0),
                            'content': getattr(result, 'text', 'Content found')
                        })
                
                return {
                    'response': response,
                    'timestamps': timestamps,
                    'search_results': search_results
                }
                
            except AttributeError:
                # If search is not available, provide a generic response
                response_prompt = PromptTemplate(
                    input_variables=["query"],
                    template="""
                    The user is asking about a video: {query}
                    
                    Since search functionality is not available, provide a helpful response
                    explaining that specific video querying requires the video to be properly
                    indexed and the search functionality to be available.
                    """
                )
                
                response_chain = LLMChain(llm=self.llm, prompt=response_prompt)
                response = response_chain.run(query=query)
                
                return {
                    'response': response,
                    'timestamps': [],
                    'search_results': None
                }
            
        except Exception as e:
            return {
                'response': f"Error querying video: {str(e)}. Please try re-uploading the video.",
                'timestamps': [],
                'search_results': None
            }
    
    def create_compilation(self, video_id: str, criteria: str, max_duration: int = 180) -> str:
        """Create video compilation based on criteria"""
        try:
            # Get video object
            if hasattr(self, '_current_video') and self._current_video.id == video_id:
                video = self._current_video
            else:
                raise Exception("Video object not found. Please re-upload the video.")
            
            # Search for relevant segments
            search_results = video.search(criteria)
            
            # Create compilation using VideoDB Timeline
            from videodb import Timeline
            timeline = Timeline(conn=self.conn)
            
            total_duration = 0
            if hasattr(search_results, 'shots'):
                for shot in search_results.shots:
                    if total_duration + (shot.end - shot.start) <= max_duration:
                        timeline.add_inline(shot)
                        total_duration += (shot.end - shot.start)
                    else:
                        break
            
            # Generate compilation
            compilation = timeline.generate()
            return getattr(compilation, 'stream_url', 'Compilation created successfully')
            
        except Exception as e:
            raise Exception(f"Compilation feature not fully implemented: {str(e)}")
    
    def store_video_reference(self, video):
        """Store video reference for later queries"""
        self._current_video = video