from videodb import connect
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import Dict, List, Optional, Any
import tempfile
import os
import streamlit as st
from src.utils.config import Config

class VideoProcessor:
    def __init__(self):
        self.conn = None
        self.llm = None
        self.initialize_clients()
    
    def _wait_for_transcript(self, video, max_wait_time=300, check_interval=10, progress_callback=None, status_callback=None):
        """Wait for transcript generation to complete using correct VideoDB methods"""
        import time
        
        start_time = time.time()
        attempts = 0
        max_attempts = max_wait_time // check_interval
        
        while time.time() - start_time < max_wait_time:
            attempts += 1
            try:
                # Update progress and status if callbacks provided
                if progress_callback and status_callback:
                    progress = min(40 + (attempts / max_attempts) * 40, 80)  # 40-80% range
                    progress_callback(progress)
                    status_callback(f"⏳ Generating transcript... (Attempt {attempts}/{max_attempts})")
                
                # Use the correct VideoDB method to get transcript text
                if status_callback:
                    status_callback(f"🔍 Attempting to retrieve transcript text (attempt {attempts})...")
                
                # Try the documented method first
                try:
                    transcript_text = video.get_transcript_text()
                    if status_callback:
                        status_callback(f"✅ Got transcript via get_transcript_text() (length: {len(transcript_text) if transcript_text else 0})")
                    
                    if transcript_text and len(transcript_text.strip()) > 10:
                        if status_callback:
                            preview = transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text
                            status_callback(f"📄 Transcript preview: {preview}")
                        return transcript_text
                    else:
                        if status_callback:
                            status_callback("⚠️ get_transcript_text() returned empty or very short content")
                
                except Exception as text_error:
                    if status_callback:
                        status_callback(f"❌ get_transcript_text() failed: {str(text_error)[:100]}")
                
                # Fallback to JSON method if text method fails
                try:
                    transcript_json = video.get_transcript()
                    if status_callback:
                        status_callback(f"🔍 Trying JSON transcript method...")
                    
                    if transcript_json:
                        transcript_text = ""
                        
                        # Handle different JSON transcript formats
                        if isinstance(transcript_json, str):
                            transcript_text = transcript_json
                        elif isinstance(transcript_json, dict):
                            # Try common JSON fields
                            for field in ['text', 'transcript', 'content', 'speech_text']:
                                if field in transcript_json and transcript_json[field]:
                                    transcript_text = transcript_json[field]
                                    break
                        elif isinstance(transcript_json, list):
                            # Handle list of transcript segments
                            text_parts = []
                            for item in transcript_json:
                                if isinstance(item, dict):
                                    for field in ['text', 'transcript', 'content']:
                                        if field in item and item[field]:
                                            text_parts.append(str(item[field]))
                                            break
                                elif isinstance(item, str):
                                    text_parts.append(item)
                            transcript_text = " ".join(text_parts)
                        elif hasattr(transcript_json, 'text'):
                            transcript_text = transcript_json.text
                        else:
                            transcript_text = str(transcript_json)
                        
                        if transcript_text and len(transcript_text.strip()) > 10:
                            if status_callback:
                                status_callback(f"✅ Extracted from JSON transcript (length: {len(transcript_text)})")
                                preview = transcript_text[:200] + "..." if len(transcript_text) > 200 else transcript_text
                                status_callback(f"📄 JSON transcript preview: {preview}")
                            return transcript_text
                        else:
                            if status_callback:
                                status_callback("⚠️ JSON transcript extraction resulted in empty content")
                
                except Exception as json_error:
                    if status_callback:
                        status_callback(f"❌ get_transcript() JSON method failed: {str(json_error)[:100]}")
                
                # If both methods fail, wait and retry
                if attempts < max_attempts:
                    if status_callback:
                        status_callback(f"⏳ Both methods failed, waiting {check_interval} seconds before retry...")
                    time.sleep(check_interval)
                    continue
                else:
                    break
                
            except Exception as e:
                error_msg = str(e).lower()
                if status_callback:
                    status_callback(f"❌ Transcript attempt {attempts} failed: {str(e)[:100]}")
                
                if "does not exist" in error_msg or "not found" in error_msg or "processing" in error_msg:
                    if status_callback:
                        status_callback(f"⏳ Transcript still processing, waiting {check_interval} seconds...")
                    time.sleep(check_interval)
                    continue
                else:
                    if attempts < 3:
                        if status_callback:
                            status_callback(f"⚠️ Error but retrying: {str(e)[:50]}")
                        time.sleep(check_interval)
                        continue
                    else:
                        raise e
        
        raise Exception(f"Transcript generation timed out after {max_wait_time} seconds. Both get_transcript_text() and get_transcript() methods failed.")
    
    def initialize_clients(self):
        """Initialize VideoDB and LangChain clients"""
        try:
            if Config.VIDEODB_API_KEY:
                self.conn = connect(api_key=Config.VIDEODB_API_KEY)
            
            if Config.GOOGLE_API_KEY:
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash", 
                    google_api_key=Config.GOOGLE_API_KEY
                )
        except Exception as e:
            if 'st' in globals():
                st.error(f"Error initializing clients: {e}")
            else:
                print(f"Error initializing clients: {e}")
    
    def process_video(self, uploaded_file=None, video_url=None, title="", description="", 
                     progress_bar=None, status_text=None) -> Dict[str, Any]:
        """Process video and extract analysis with enhanced debugging"""
        if not self.conn or not self.llm:
            raise Exception("Clients not properly initialized. Check API keys.")
        
        def update_progress(progress):
            if progress_bar:
                progress_bar.progress(progress)
        
        def update_status(status):
            if status_text:
                status_text.text(status)
            print(f"DEBUG: {status}")  # Also log to console for debugging
        
        try:
            # Upload video to VideoDB
            update_status("📤 Uploading video to VideoDB...")
            update_progress(10)
            
            video = None
            if uploaded_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    video_path = tmp_file.name
                
                update_status(f"📤 Uploading file: {uploaded_file.name}")
                video = self.conn.upload(path=video_path)
                os.unlink(video_path)
                
            elif video_url:
                update_status(f"📤 Uploading from URL: {video_url[:50]}...")
                video = self.conn.upload(url=video_url)
            else:
                raise ValueError("Either uploaded_file or video_url must be provided")
            
            update_status(f"✅ Video uploaded successfully! ID: {video.id}")
            update_progress(20)
            
            # Generate stream for the video
            update_status("🎬 Processing video stream...")
            video.generate_stream()
            update_progress(30)
            
            # Enhanced transcript generation with correct VideoDB methods
            update_status("📝 Starting transcript generation...")
            transcript_text = ""
            
            try:
                # Check video properties first
                update_status("🔍 Checking video properties...")
                video_info = {
                    'id': getattr(video, 'id', 'Unknown'),
                    'name': getattr(video, 'name', 'Unknown'),  
                    'duration': getattr(video, 'duration', 'Unknown'),
                    'status': getattr(video, 'status', 'Unknown')
                }
                update_status(f"📊 Video info: {video_info}")
                
                # Generate transcript using VideoDB
                update_status("🎤 Initiating transcript generation...")
                video.generate_transcript()
                update_progress(40)
                
                # Wait for transcript using the correct methods
                transcript_text = self._wait_for_transcript(
                    video, 
                    max_wait_time=300,  # 5 minutes
                    progress_callback=update_progress,
                    status_callback=update_status
                )
                
                if transcript_text and len(transcript_text.strip()) > 50:
                    update_status(f"✅ Transcript retrieved successfully! Length: {len(transcript_text)} chars")
                    # Show a clean preview
                    clean_preview = transcript_text.strip()[:200] + "..." if len(transcript_text.strip()) > 200 else transcript_text.strip()
                    update_status(f"📄 Content preview: {clean_preview}")
                    update_progress(80)
                else:
                    update_status(f"⚠️ Transcript seems incomplete or empty")
                    # Try immediate methods as final attempt
                    try:
                        update_status("🔄 Trying immediate transcript retrieval...")
                        transcript_text = video.get_transcript_text()
                        if not transcript_text:
                            # Try JSON method
                            text_json = video.get_transcript()
                            if isinstance(text_json, str):
                                transcript_text = text_json
                            elif hasattr(text_json, 'text'):
                                transcript_text = text_json.text
                            else:
                                transcript_text = str(text_json) if text_json else ""
                        
                        if transcript_text and len(transcript_text.strip()) > 10:
                            update_status(f"✅ Retrieved transcript via immediate method! Length: {len(transcript_text)}")
                        else:
                            update_status("❌ All transcript methods returned empty content")
                            
                    except Exception as immediate_error:
                        update_status(f"❌ Immediate transcript methods failed: {str(immediate_error)}")
                    
            except Exception as e:
                update_status(f"❌ Transcript generation failed: {str(e)}")
                
                # Enhanced fallback strategies
                try:
                    update_status("🔄 Trying alternative: Scene indexing...")
                    scenes = video.index_scenes(
                        prompt="Extract and transcribe all spoken dialogue, narration, and text shown in this scene. Include all spoken content."
                    )
                    update_status(f"📋 Scene indexing initiated: {scenes}")
                    transcript_text = "Video processed with scene indexing. Content analysis available through search functionality."
                    
                except Exception as scene_error:
                    update_status(f"❌ Scene indexing failed: {str(scene_error)}")
                    
                    try:
                        update_status("🔄 Trying spoken word indexing...")
                        spoken_index = video.index_spoken_words()
                        update_status(f"🗣️ Spoken word indexing initiated: {spoken_index}")
                        transcript_text = "Video processed with spoken word indexing. Speech content is searchable."
                        
                    except Exception as spoken_error:
                        update_status(f"❌ All indexing methods failed: {str(spoken_error)}")
                        transcript_text = f"Video uploaded successfully but transcript extraction failed. Error: {str(e)[:100]}. The video is available for basic analysis."
            
            # Generate analysis
            update_status("🤖 Analyzing content with AI...")
            update_progress(85)
            
            analysis = self._analyze_content(transcript_text, title, description, update_status)
            analysis['video_id'] = video.id
            analysis['video_object'] = video
            analysis['transcript_length'] = len(transcript_text)
            analysis['raw_transcript_preview'] = transcript_text[:500] if transcript_text else "No transcript"
            
            update_status("✅ Analysis complete!")
            update_progress(100)
            
            return analysis
            
        except Exception as e:
            update_status(f"❌ Critical error: {str(e)}")
            raise Exception(f"Error processing video: {str(e)}")
    
    def _analyze_content(self, transcript: str, title: str, description: str, status_callback=None) -> Dict[str, Any]:
        """Analyze video content with enhanced debugging"""
        
        if status_callback:
            status_callback(f"🧠 Analyzing content. Transcript length: {len(transcript)} chars")
        
        # Check content quality
        content_quality = "high" if len(transcript) > 500 else "low" if len(transcript) > 50 else "minimal"
        
        if status_callback:
            status_callback(f"📊 Content quality: {content_quality}")
        
        # Enhanced prompt based on content quality
        if content_quality == "high":
            template = """
            Analyze the following video content and provide a comprehensive analysis.
            
            Title: {title}
            Description: {description}
            Transcript: {transcript}
            
            Provide a detailed analysis with:
            1. A comprehensive summary (3-4 sentences)
            2. Key topics discussed (5-7 specific topics)
            3. Important quotes or key points (5-8 actual quotes from the content)
            
            Format:
            SUMMARY: [detailed summary based on actual content]
            TOPICS: [specific topic1, specific topic2, etc.]
            QUOTES: [actual quote 1 | actual quote 2 | etc.]
            """
        else:
            template = """
            Limited content available for analysis.
            Title: {title}
            Description: {description}
            Available content: {transcript}
            
            Based on the available information, provide:
            SUMMARY: A summary noting the limited content available
            TOPICS: General topics that can be inferred
            QUOTES: Note that specific quotes are not available due to transcript issues
            
            Be honest about the limitations.
            """
        
        summary_prompt = PromptTemplate(
            input_variables=["transcript", "title", "description"],
            template=template
        )
        
        summary_chain = LLMChain(llm=self.llm, prompt=summary_prompt)
        
        if status_callback:
            status_callback("🤖 Running AI analysis...")
        
        result = summary_chain.run(
            transcript=transcript[:4000] if transcript else "No transcript available",
            title=title or "Untitled Video",
            description=description or "No description provided"
        )
        
        if status_callback:
            status_callback("📊 Parsing analysis results...")
        
        analysis = self._parse_analysis_result(result)
        analysis['content_quality'] = content_quality
        analysis['analysis_source'] = f"Based on {len(transcript)} characters of content"
        
        return analysis
    
    def _parse_analysis_result(self, result: str) -> Dict[str, Any]:
        """Parse the LLM analysis result with better error handling"""
        analysis = {
            'summary': '',
            'topics': [],
            'key_quotes': [],
            'raw_analysis': result  # Keep raw result for debugging
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
        
        # Enhanced fallback parsing
        if not analysis['summary'] and result:
            # Try to extract first meaningful paragraph as summary
            paragraphs = [p.strip() for p in result.split('\n\n') if p.strip()]
            analysis['summary'] = paragraphs[0] if paragraphs else result[:300]
        
        return analysis
    
    def query_video(self, query: str, video_id: str) -> Dict[str, Any]:
        """Query specific information from the video"""
        try:
            if hasattr(self, '_current_video') and self._current_video.id == video_id:
                video = self._current_video
            else:
                raise Exception("Video object not found. Please re-upload the video.")
            
            try:
                search_results = video.search(query)
                
                response_prompt = PromptTemplate(
                    input_variables=["query", "search_results"],
                    template="""
                    Answer the user's question based on the video search results.
                    
                    Question: {query}
                    Search Results: {search_results}
                    
                    Provide a clear answer with relevant timestamps if available.
                    """
                )
                
                response_chain = LLMChain(llm=self.llm, prompt=response_prompt)
                response = response_chain.run(query=query, search_results=str(search_results))
                
                timestamps = []
                if hasattr(search_results, 'shots'):
                    for shot in search_results.shots[:5]:
                        timestamps.append({
                            'start': shot.start,
                            'end': shot.end,
                            'content': getattr(shot, 'text', 'Content found')
                        })
                
                return {
                    'response': response,
                    'timestamps': timestamps,
                    'search_results': search_results
                }
                
            except AttributeError:
                response = f"I cannot search the video content directly. The video may not have been properly indexed. You asked: '{query}'. Please try re-uploading the video or contact support if the issue persists."
                
                return {
                    'response': response,
                    'timestamps': [],
                    'search_results': None
                }
            
        except Exception as e:
            return {
                'response': f"Error querying video: {str(e)}",
                'timestamps': [],
                'search_results': None
            }
    
    def create_compilation(self, video_id: str, criteria: str, max_duration: int = 180) -> str:
        """Create video compilation based on criteria"""
        try:
            if hasattr(self, '_current_video') and self._current_video.id == video_id:
                video = self._current_video
            else:
                raise Exception("Video object not found. Please re-upload the video.")
            
            search_results = video.search(criteria)
            
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
            
            compilation = timeline.generate()
            return getattr(compilation, 'stream_url', 'Compilation created successfully')
            
        except Exception as e:
            raise Exception(f"Compilation feature not fully implemented: {str(e)}")
    
    def store_video_reference(self, video):
        """Store video reference for later queries"""
        self._current_video = video