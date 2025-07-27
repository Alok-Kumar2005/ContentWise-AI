import streamlit as st
import os
from datetime import datetime
import logging
import atexit

from services.videodb_service import VideoDBService
from services.llm_service import LLMService
from services.social_media_generator import SocialMediaGenerator
from services.rag_service import RAGService
from models.video_processor import VideoAnalysis, TimestampQuery
from utils.helpers import save_uploaded_file, validate_video_url, format_timestamp

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize services
@st.cache_resource
def init_services():
    services = {}
    try:
        services['videodb'] = VideoDBService()
        services['llm'] = LLMService()
        services['social_media'] = SocialMediaGenerator()
        # Don't cache RAG service as it needs to be session-specific
        logging.info("Core services initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing services: {e}")
        raise
    return services

def init_rag_service():
    """Initialize RAG service for the session"""
    try:
        return RAGService()
    except Exception as e:
        logging.error(f"Error initializing RAG service: {e}")
        return None

# Cleanup function for when the app closes
def cleanup_rag():
    if 'rag_service' in st.session_state:
        st.session_state.rag_service.cleanup()

# Register cleanup function
atexit.register(cleanup_rag)

def main():
    st.set_page_config(
        page_title="AI-Powered Video Analysis with RAG",
        page_icon="🎥",
        layout="wide"
    )
    
    st.title("🎥 AI-Powered Video Analysis with RAG")
    st.markdown("Upload your video or provide a URL to get AI-powered analysis, summaries, social media posts, and intelligent Q&A!")
    
    # Initialize services
    try:
        services = init_services()
        # Initialize RAG service for this session if not already done
        if 'rag_service' not in st.session_state:
            rag_service = init_rag_service()
            if rag_service:
                st.session_state.rag_service = rag_service
            else:
                st.error("Failed to initialize RAG service. Q&A functionality will not be available.")
    except Exception as e:
        st.error(f"Error initializing services: {e}")
        st.stop()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        st.info("Make sure to set your API keys in environment variables:\n- VIDEODB_API_KEY\n- GOOGLE_API_KEY")
        
        # RAG Database Status
        if 'rag_service' in st.session_state and st.session_state.rag_service:
            stats = st.session_state.rag_service.get_database_stats()
            st.subheader("📊 RAG Database Status")
            st.write(f"**Status:** {stats['status']}")
            st.write(f"**Text Chunks:** {stats['chunks']}")
            
            if st.button("🗑️ Clear RAG Database"):
                try:
                    st.session_state.rag_service.cleanup()
                    new_rag_service = init_rag_service()
                    if new_rag_service:
                        st.session_state.rag_service = new_rag_service
                        st.success("RAG database cleared!")
                    else:
                        st.error("Failed to reinitialize RAG service")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error clearing RAG database: {e}")
        else:
            st.subheader("📊 RAG Database Status")
            st.write("**Status:** Not initialized")
            if st.button("🔄 Initialize RAG Service"):
                rag_service = init_rag_service()
                if rag_service:
                    st.session_state.rag_service = rag_service
                    st.success("RAG service initialized!")
                    st.rerun()
                else:
                    st.error("Failed to initialize RAG service")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📤 Upload & Analyze", 
        "📝 Summary & Topics", 
        "📱 Social Media Posts", 
        "🔍 Timestamp Search",
        "🤖 AI Q&A (RAG)"
    ])
    
    with tab1:
        st.header("1. Provide Your Content")
        
        # Video input options
        input_type = st.radio("Choose input method:", ["Video File", "Video URL"])
        
        video_title = st.text_input("Video Title (Optional)")
        video_description = st.text_area("Video Description (Optional)")
        
        video = None
        
        if input_type == "Video File":
            uploaded_file = st.file_uploader(
                "Choose a video file",
                type=['mp4', 'avi', 'mov', 'mkv', 'webm']
            )
            
            if uploaded_file and st.button("🔄 Analyze Video"):
                with st.spinner("Uploading and processing video..."):
                    try:
                        # Save uploaded file
                        temp_path = save_uploaded_file(uploaded_file)
                        
                        # Upload to VideoDB
                        video = services['videodb'].upload_video(temp_path, "file")
                        
                        # Clean up temp file
                        os.unlink(temp_path)
                        
                        st.session_state.video = video
                        st.session_state.video_title = video_title or uploaded_file.name
                        st.success("✅ Video uploaded and indexed successfully!")
                        
                    except Exception as e:
                        st.error(f"Error processing video: {e}")
        
        else:  # Video URL
            video_url = st.text_input("Enter video URL (YouTube, Vimeo, etc.)")
            
            if video_url and st.button("🔄 Analyze Video"):
                if validate_video_url(video_url):
                    with st.spinner("Processing video from URL..."):
                        try:
                            # Upload to VideoDB
                            video = services['videodb'].upload_video(video_url, "url")
                            
                            st.session_state.video = video
                            st.session_state.video_title = video_title or "Video from URL"
                            st.success("✅ Video processed and indexed successfully!")
                            
                        except Exception as e:
                            st.error(f"Error processing video: {e}")
                else:
                    st.error("Please enter a valid video URL")
    
    with tab2:
        st.header("2. AI-Powered Analysis")
        
        if 'video' in st.session_state:
            video = st.session_state.video
            
            if st.button("📊 Generate Summary"):
                with st.spinner("Generating AI analysis and creating RAG database..."):
                    try:
                        # Get transcript
                        transcript = services['videodb'].get_transcript(video)
                        
                        if not transcript:
                            st.error("Could not extract transcript from video")
                            return
                        
                        # Generate summary
                        summary = services['llm'].generate_summary(
                            transcript, 
                            st.session_state.get('video_title', '')
                        )
                        
                        # Extract key topics
                        topics = services['llm'].extract_key_topics(transcript)
                        
                        # Create RAG vector database
                        if 'rag_service' in st.session_state and st.session_state.rag_service:
                            rag_success = st.session_state.rag_service.create_vector_database(
                                transcript, 
                                st.session_state.get('video_title', '')
                            )
                        else:
                            rag_success = False
                            st.warning("RAG service not available. Q&A functionality will be limited.")
                        
                        # Store in session state
                        st.session_state.transcript = transcript
                        st.session_state.summary = summary
                        st.session_state.topics = topics
                        
                        # Display results
                        st.subheader("📄 Summary")
                        st.write(summary)
                        
                        st.subheader("🔑 Key Topics")
                        for i, topic in enumerate(topics, 1):
                            st.write(f"{i}. {topic}")
                        
                        # RAG Database Status
                        if rag_success:
                            st.success("✅ RAG database created successfully! You can now ask questions about the video content.")
                        else:
                            st.warning("⚠️ RAG database creation failed. Q&A feature may not work properly.")
                        
                        st.subheader("📜 Full Transcript")
                        with st.expander("View full transcript"):
                            st.text_area("Transcript", transcript, height=300)
                        
                    except Exception as e:
                        st.error(f"Error generating analysis: {e}")
        else:
            st.info("Please upload and analyze a video first.")
    
    with tab3:
        st.header("3. Generate Social Media Posts")
        
        if 'summary' in st.session_state and 'topics' in st.session_state:
            platforms = st.multiselect(
                "Select platforms:",
                ["LinkedIn", "Twitter", "Instagram", "Facebook"],
                default=["LinkedIn", "Twitter"]
            )
            
            if st.button("🚀 Generate Social Media Posts"):
                with st.spinner("Creating social media content..."):
                    posts = {}
                    
                    for platform in platforms:
                        try:
                            if platform == "LinkedIn":
                                post = services['social_media'].generate_linkedin_post(
                                    st.session_state.summary,
                                    st.session_state.topics
                                )
                            elif platform == "Twitter":
                                post = services['social_media'].generate_twitter_post(
                                    st.session_state.summary,
                                    st.session_state.topics
                                )
                            elif platform == "Instagram":
                                post = services['social_media'].generate_instagram_post(
                                    st.session_state.summary,
                                    st.session_state.topics
                                )
                            elif platform == "Facebook":
                                post = services['social_media'].generate_facebook_post(
                                    st.session_state.summary,
                                    st.session_state.topics
                                )
                            
                            posts[platform] = post
                        except Exception as e:
                            st.error(f"Error generating {platform} post: {e}")
                    
                    # Display posts
                    for platform, post in posts.items():
                        st.subheader(f"📱 {platform} Post")
                        st.text_area(
                            f"{platform} Content",
                            post.content,
                            height=200,
                            key=f"{platform}_content"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Character Count:** {post.character_count}")
                        with col2:
                            if post.hashtags:
                                st.write(f"**Hashtags:** {', '.join(post.hashtags)}")
                        
                        st.markdown("---")
        else:
            st.info("Please generate video analysis first.")
    
    with tab4:
        st.header("4. Timestamp Search")
        
        if 'video' in st.session_state:
            query = st.text_input("Search for specific content in the video:")
            
            if query and st.button("🔍 Search"):
                with st.spinner("Searching video content..."):
                    try:
                        search_results = services['videodb'].search_video_content(
                            st.session_state.video,
                            query
                        )
                        
                        if search_results['results']:
                            st.subheader("Search Results")
                            
                            for i, (start, end) in enumerate(search_results['timestamps']):
                                st.write(f"**Result {i+1}:** {format_timestamp(start)} - {format_timestamp(end)}")
                            
                            if search_results['playable_url']:
                                st.video(search_results['playable_url'])
                        else:
                            st.info("No results found for your query.")
                    
                    except Exception as e:
                        st.error(f"Error searching video: {e}")
        else:
            st.info("Please upload and analyze a video first.")
    
    with tab5:
        st.header("5. AI Q&A with RAG")
        st.markdown("Ask questions about the video content using Retrieval-Augmented Generation (RAG)")
        
        if 'rag_service' in st.session_state and st.session_state.rag_service:
            stats = st.session_state.rag_service.get_database_stats()
            
            if stats['chunks'] > 0:
                st.success(f"✅ RAG database ready with {stats['chunks']} text chunks")
                
                # Chat interface for Q&A
                if 'rag_messages' not in st.session_state:
                    st.session_state.rag_messages = []
                
                # Display chat history
                for message in st.session_state.rag_messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                
                # Chat input
                if prompt := st.chat_input("Ask a question about the video content..."):
                    # Add user message to chat history
                    st.session_state.rag_messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)
                    
                    # Generate RAG response
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            try:
                                response = st.session_state.rag_service.query_video_content(prompt)
                                st.markdown(response)
                                # Add assistant response to chat history
                                st.session_state.rag_messages.append({"role": "assistant", "content": response})
                            except Exception as e:
                                error_msg = f"Error generating response: {str(e)}"
                                st.error(error_msg)
                                st.session_state.rag_messages.append({"role": "assistant", "content": error_msg})
                
                # Clear chat button
                if st.button("🗑️ Clear Chat History"):
                    st.session_state.rag_messages = []
                    st.rerun()
                
            else:
                st.info("Please upload and analyze a video first to enable Q&A functionality.")
                st.markdown("**Steps:**")
                st.markdown("1. Go to 'Upload & Analyze' tab")
                st.markdown("2. Upload a video or provide a URL")
                st.markdown("3. Click 'Analyze Video'")
                st.markdown("4. Go to 'Summary & Topics' and click 'Generate Summary'")
                st.markdown("5. Return here to ask questions!")
        else:
            st.error("RAG service not initialized properly")
            if st.button("🔄 Try to Initialize RAG Service"):
                rag_service = init_rag_service()
                if rag_service:
                    st.session_state.rag_service = rag_service
                    st.success("RAG service initialized!")
                    st.rerun()
                else:
                    st.error("Failed to initialize RAG service")

if __name__ == "__main__":
    main()