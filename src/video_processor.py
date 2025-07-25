from videodb import connect, SearchType, IndexType
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
    
    def _wait_for_indexing(self, video, max_wait_time=300, check_interval=10, progress_callback=None, status_callback=None):
        """Wait for video indexing to complete"""
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
                    status_callback(f"⏳ Indexing video content... (Attempt {attempts}/{max_attempts})")
                
                # Try to search for any content to check if indexing is complete
                test_result = video.search(
                    query="test", 
                    search_type=SearchType.semantic,
                    index_type=IndexType.spoken_word
                )
                
                if test_result and hasattr(test_result, 'shots'):
                    if status_callback:
                        status_callback(f"✅ Video indexing completed successfully!")
                    return True
                
                if status_callback:
                    status_callback(f"⏳ Still indexing, waiting {check_interval} seconds...")
                time.sleep(check_interval)
                
            except Exception as e:
                error_msg = str(e).lower()
                if "indexing" in error_msg or "processing" in error_msg or "not ready" in error_msg:
                    if status_callback:
                        status_callback(f"⏳ Video still processing, waiting {check_interval} seconds...")
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
        
        raise Exception(f"Video indexing timed out after {max_wait_time} seconds.")
    
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
        """Process video and extract analysis using correct VideoDB methods"""
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
                video = self.conn.upload(file_path=video_path)  # Correct parameter name
                os.unlink(video_path)
                
            elif video_url:
                update_status(f"📤 Uploading from URL: {video_url[:50]}...")
                video = self.conn.upload(url=video_url)
            else:
                raise ValueError("Either uploaded_file or video_url must be provided")
            
            update_status(f"✅ Video uploaded successfully! ID: {video.id}")
            update_progress(30)
            
            # Index the video for spoken words (this automatically handles transcription)
            update_status("🎤 Indexing video for spoken content...")
            video.index_spoken_words()
            update_progress(50)
            
            # Wait for indexing to complete
            update_status("⏳ Waiting for video indexing to complete...")
            self._wait_for_indexing(
                video,
                max_wait_time=300,  # 5 minutes
                progress_callback=update_progress,
                status_callback=update_status
            )
            
            update_progress(70)
            
            # Extract content by searching for general topics
            update_status("📄 Extracting video content...")
            content_text = self._extract_video_content(video, update_status)
            
            update_progress(85)
            
            # Generate analysis
            update_status("🤖 Analyzing content with AI...")
            analysis = self._analyze_content(content_text, title, description, update_status)
            analysis['video_id'] = video.id
            analysis['video_object'] = video
            analysis['content_length'] = len(content_text)
            analysis['content_preview'] = content_text[:500] if content_text else "No content extracted"
            
            update_status("✅ Analysis complete!")
            update_progress(100)
            
            return analysis
            
        except Exception as e:
            update_status(f"❌ Critical error: {str(e)}")
            raise Exception(f"Error processing video: {str(e)}")
    
    def _extract_video_content(self, video, status_callback=None):
        """Extract video content using search functionality"""
        try:
            if status_callback:
                status_callback("🔍 Extracting spoken content...")
            
            # Search for broad topics to get comprehensive content
            search_queries = [
                "main topic discussion",
                "important points",
                "key information",
                "summary content",
                "speaking conversation"
            ]
            
            all_content = []
            
            for query in search_queries:
                try:
                    if status_callback:
                        status_callback(f"🔍 Searching for: {query}")
                    
                    result = video.search(
                        query=query,
                        search_type=SearchType.semantic,
                        index_type=IndexType.spoken_word
                    )
                    
                    if result and hasattr(result, 'shots'):
                        for shot in result.shots[:10]:  # Limit to first 10 results per query
                            if hasattr(shot, 'text') and shot.text:
                                all_content.append(shot.text)
                            elif hasattr(shot, 'transcript') and shot.transcript:
                                all_content.append(shot.transcript)
                    
                except Exception as search_error:
                    if status_callback:
                        status_callback(f"⚠️ Search failed for '{query}': {str(search_error)[:50]}")
                    continue
            
            # Combine and deduplicate content
            combined_content = " ".join(all_content)
            
            # Remove duplicates by splitting into sentences and deduplicating
            sentences = combined_content.split('.')
            unique_sentences = list(dict.fromkeys(sentences))  # Preserve order while removing duplicates
            final_content = '. '.join(unique_sentences)
            
            if status_callback:
                status_callback(f"✅ Extracted {len(final_content)} characters of content")
            
            return final_content if final_content.strip() else "Content extraction completed but no text content found."
            
        except Exception as e:
            if status_callback:
                status_callback(f"❌ Content extraction failed: {str(e)}")
            return f"Content extraction failed: {str(e)}"
    
    def _analyze_content(self, content: str, title: str, description: str, status_callback=None) -> Dict[str, Any]:
        """Analyze video content with enhanced debugging"""
        
        if status_callback:
            status_callback(f"🧠 Analyzing content. Content length: {len(content)} chars")
        
        # Check content quality
        content_quality = "high" if len(content) > 500 else "low" if len(content) > 50 else "minimal"
        
        if status_callback:
            status_callback(f"📊 Content quality: {content_quality}")
        
        # Enhanced prompt based on content quality
        if content_quality == "high":
            template = """
            Analyze the following video content and provide a comprehensive analysis.
            
            Title: {title}
            Description: {description}
            Content: {content}
            
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
            Available content: {content}
            
            Based on the available information, provide:
            SUMMARY: A summary noting the limited content available
            TOPICS: General topics that can be inferred
            QUOTES: Note that specific quotes are not available due to content extraction issues
            
            Be honest about the limitations.
            """
        
        summary_prompt = PromptTemplate(
            input_variables=["content", "title", "description"],
            template=template
        )
        
        summary_chain = LLMChain(llm=self.llm, prompt=summary_prompt)
        
        if status_callback:
            status_callback("🤖 Running AI analysis...")
        
        result = summary_chain.run(
            content=content[:4000] if content else "No content available",
            title=title or "Untitled Video",
            description=description or "No description provided"
        )
        
        if status_callback:
            status_callback("📊 Parsing analysis results...")
        
        analysis = self._parse_analysis_result(result)
        analysis['content_quality'] = content_quality
        analysis['analysis_source'] = f"Based on {len(content)} characters of content"
        
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
        """Query specific information from the video using correct VideoDB search"""
        try:
            if hasattr(self, '_current_video') and self._current_video.id == video_id:
                video = self._current_video
            else:
                raise Exception("Video object not found. Please re-upload the video.")
            
            try:
                # Use correct search parameters
                search_results = video.search(
                    query=query,
                    search_type=SearchType.semantic,
                    index_type=IndexType.spoken_word
                )
                
                # Extract relevant content from search results
                relevant_content = []
                timestamps = []
                
                if hasattr(search_results, 'shots'):
                    for shot in search_results.shots[:5]:  # Limit to top 5 results
                        if hasattr(shot, 'text') and shot.text:
                            relevant_content.append(shot.text)
                        
                        timestamps.append({
                            'start': getattr(shot, 'start', 0),
                            'end': getattr(shot, 'end', 0),
                            'content': getattr(shot, 'text', 'Content found')
                        })
                
                # Generate response using LLM
                response_prompt = PromptTemplate(
                    input_variables=["query", "search_content"],
                    template="""
                    Answer the user's question based on the video search results.
                    
                    Question: {query}
                    Relevant Content: {search_content}
                    
                    Provide a clear and comprehensive answer based on the content found.
                    """
                )
                
                response_chain = LLMChain(llm=self.llm, prompt=response_prompt)
                response = response_chain.run(
                    query=query, 
                    search_content=" ".join(relevant_content) if relevant_content else "No relevant content found"
                )
                
                return {
                    'response': response,
                    'timestamps': timestamps,
                    'search_results': search_results
                }
                
            except Exception as search_error:
                response = f"I cannot search the video content. Error: {str(search_error)}. The video may need to be re-indexed or the search functionality is not available."
                
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
        """Create video compilation based on criteria using correct VideoDB methods"""
        try:
            if hasattr(self, '_current_video') and self._current_video.id == video_id:
                video = self._current_video
            else:
                raise Exception("Video object not found. Please re-upload the video.")
            
            # Search for relevant content
            search_results = video.search(
                query=criteria,
                search_type=SearchType.semantic,
                index_type=IndexType.spoken_word
            )
            
            # Create timeline for compilation
            from videodb import Timeline
            timeline = Timeline(conn=self.conn)
            
            total_duration = 0
            if hasattr(search_results, 'shots'):
                for shot in search_results.shots:
                    shot_duration = getattr(shot, 'end', 0) - getattr(shot, 'start', 0)
                    if total_duration + shot_duration <= max_duration:
                        timeline.add_inline(shot)
                        total_duration += shot_duration
                    else:
                        break
            
            # Generate the compilation
            compilation = timeline.generate()
            return getattr(compilation, 'stream_url', 'Compilation created successfully')
            
        except Exception as e:
            raise Exception(f"Error creating compilation: {str(e)}")
    
    def store_video_reference(self, video):
        """Store video reference for later queries"""
        self._current_video = video