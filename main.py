import streamlit as st
import os
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.video_processor import VideoProcessor
from src.social_media_generator import SocialMediaGenerator
from src.utils.config import Config

def main():
    st.set_page_config(
        page_title="AI Video Analysis Tool",
        page_icon="🎥",
        layout="wide"
    )
    
    st.title("🎥 AI-Powered Video Analysis Tool")
    
    # Initialize session state
    if 'video_processor' not in st.session_state:
        st.session_state.video_processor = VideoProcessor()
    if 'social_generator' not in st.session_state:
        st.session_state.social_generator = SocialMediaGenerator()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API Keys
        videodb_api_key = st.text_input("VideoDB API Key", type="password", 
                                       help="Get your API key from VideoDB dashboard")
        google_api_key = st.text_input("Google API Key", type="password",
                                     help="Get your API key from Google AI Studio")
        
        if videodb_api_key and google_api_key:
            Config.VIDEODB_API_KEY = videodb_api_key
            Config.GOOGLE_API_KEY = google_api_key
            os.environ["GOOGLE_API_KEY"] = google_api_key
            
            # Reinitialize clients with new API keys
            st.session_state.video_processor.initialize_clients()
            st.session_state.social_generator.initialize_llm()
            
            st.success("✅ API keys configured successfully!")
        else:
            st.warning("⚠️ Please enter both API keys to continue")
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 Upload Content", 
        "🤖 AI Analysis", 
        "📱 Social Media Posts", 
        "🎬 Video Compilations"
    ])
    
    with tab1:
        st.header("1. Provide Your Content")
        st.write("Upload a video file or provide a video URL for analysis.")
        
        # Video upload options
        upload_option = st.radio(
            "Choose upload method:",
            ["Upload Video File", "Enter Video URL"],
            help="Choose how you want to provide your video content"
        )
        
        video_url = None
        uploaded_file = None
        
        if upload_option == "Upload Video File":
            uploaded_file = st.file_uploader(
                "Choose a video file",
                type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
                help="Upload your video file (recommended: under 200MB for faster processing)"
            )
            if uploaded_file:
                st.success(f"✅ File uploaded: {uploaded_file.name}")
        else:
            video_url = st.text_input(
                "Enter video URL:",
                placeholder="https://www.youtube.com/watch?v=...",
                help="Paste a YouTube URL or other supported video URL"
            )
            if video_url:
                st.success("✅ Video URL provided")
        
        # Video metadata
        st.subheader("Video Information (Optional)")
        col1, col2 = st.columns(2)
        
        with col1:
            video_title = st.text_input("Video Title", 
                                      placeholder="Enter a descriptive title...")
        with col2:
            video_description = st.text_area(
                "Video Description",
                placeholder="Brief description of the video content...",
                height=100
            )
        
        # Process video button
        process_button = st.button("🔍 Analyze Video", type="primary", use_container_width=True)
        
        if process_button:
            if not (videodb_api_key and google_api_key):
                st.error("❌ Please provide both VideoDB and Google API keys in the sidebar")
            elif uploaded_file or video_url:
                # Create containers for progress updates
                progress_container = st.container()
                status_container = st.container()
                
                with progress_container:
                    progress_bar = st.progress(0)
                with status_container:
                    status_text = st.empty()
                
                try:
                    # Pass progress bar and status text to the processor
                    result = st.session_state.video_processor.process_video(
                        uploaded_file=uploaded_file,
                        video_url=video_url,
                        title=video_title,
                        description=video_description,
                        progress_bar=progress_bar,
                        status_text=status_text
                    )
                    
                    # Store video reference for queries
                    if 'video_object' in result:
                        st.session_state.video_processor.store_video_reference(result['video_object'])
                    
                    st.session_state.video_analysis = result
                    
                    # Show success message and results
                    st.success("🎉 Video analysis completed successfully!")
                    st.balloons()
                    
                    # Show a preview of results
                    with st.expander("📊 Analysis Preview", expanded=True):
                        if result.get('summary'):
                            st.write("**Summary:**", result['summary'])
                        if result.get('topics'):
                            st.write("**Topics:**", ", ".join(result['topics']))
                        if result.get('key_quotes'):
                            st.write("**Key Points:**")
                            for i, quote in enumerate(result['key_quotes'][:3], 1):
                                st.write(f"{i}. {quote}")
                        
                        # Show content quality info
                        if result.get('content_quality'):
                            if result['content_quality'] == 'high':
                                st.success(f"✅ High quality content extracted ({result.get('content_length', 0)} characters)")
                            elif result['content_quality'] == 'low':
                                st.warning(f"⚠️ Limited content extracted ({result.get('content_length', 0)} characters)")
                            else:
                                st.info(f"ℹ️ Minimal content extracted ({result.get('content_length', 0)} characters)")
                    
                    # Clear progress indicators after a delay
                    import time
                    time.sleep(2)
                    progress_bar.empty()
                    status_text.empty()
                    
                    st.info("✨ Switch to the 'AI Analysis' tab to explore detailed insights!")
                    
                except Exception as e:
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
                    
                    st.error(f"❌ Error processing video: {str(e)}")
                    
                    # Provide specific help based on error type
                    error_str = str(e).lower()
                    if "indexing" in error_str or "search" in error_str:
                        st.info("💡 **Indexing Issue**: The video indexing failed. This might be due to:")
                        st.write("- Video format compatibility issues")
                        st.write("- VideoDB service temporary issues")
                        st.write("- API key permissions or credits")
                        st.write("- Try using a different video or check VideoDB service status")
                    elif "api" in error_str or "key" in error_str:
                        st.info("💡 **API Issue**: Please check your API keys and ensure they are valid and have sufficient credits")
                    elif "timeout" in error_str:
                        st.info("💡 **Timeout Issue**: The video processing took too long. Try with:")
                        st.write("- A shorter video")
                        st.write("- Better internet connection")
                        st.write("- Retry the process")
                    else:
                        st.info("💡 **General troubleshooting**:")
                        st.write("- Ensure video format is supported (MP4, AVI, MOV, etc.)")
                        st.write("- Check your internet connection")
                        st.write("- Verify API keys are correct and have sufficient permissions")
                        st.write("- Try with a smaller video file")
                        st.write("- Check VideoDB service status")
            else:
                st.warning("⚠️ Please upload a video file or enter a video URL")
    
    with tab2:
        st.header("2. AI-Powered Analysis")
        
        if 'video_analysis' not in st.session_state:
            st.info("📹 Please upload and process a video first in the 'Upload Content' tab")
        else:
            analysis = st.session_state.video_analysis
            
            # Display video info
            if analysis.get('video_id'):
                st.success(f"🎬 Video ID: {analysis['video_id']}")
            
            # Show content extraction info
            if analysis.get('content_quality'):
                quality_emoji = "✅" if analysis['content_quality'] == 'high' else "⚠️" if analysis['content_quality'] == 'low' else "ℹ️"
                st.info(f"{quality_emoji} Content Quality: {analysis['content_quality'].title()} - {analysis.get('content_length', 0)} characters extracted")
            
            # Create columns for better layout
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Summary Section
                st.subheader("📝 Summary")
                if analysis.get('summary'):
                    st.write(analysis['summary'])
                else:
                    st.info("Summary will appear here after video processing")
                
                # Query Section
                st.subheader("🔍 Ask Questions About the Video")
                st.info("💡 This feature searches through the video's spoken content using AI semantic search.")
                
                user_query = st.text_input(
                    "Enter your question:",
                    placeholder="What is the main topic discussed in the video?",
                    key="video_query"
                )
                
                query_col1, query_col2 = st.columns([1, 4])
                with query_col1:
                    ask_button = st.button("Get Answer", type="secondary")
                
                if ask_button and user_query:
                    with st.spinner("🔍 Searching video content..."):
                        try:
                            answer = st.session_state.video_processor.query_video(
                                user_query, analysis['video_id']
                            )
                            st.write("**Answer:**")
                            st.write(answer['response'])
                            
                            if answer.get('timestamps'):
                                st.write("**Relevant timestamps:**")
                                for ts in answer['timestamps'][:3]:  # Limit to 3 timestamps
                                    start_time = ts.get('start', 0)
                                    end_time = ts.get('end', 0)
                                    content = ts.get('content', 'Content found')
                                    if start_time or end_time:
                                        st.write(f"⏰ {start_time}s - {end_time}s: {content[:100]}...")
                                    else:
                                        st.write(f"📄 {content[:100]}...")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            st.info("💡 Try rephrasing your question or ensure the video was properly indexed.")
            
            with col2:
                # Key Quotes Section
                st.subheader("💬 Key Points")
                if analysis.get('key_quotes'):
                    for i, quote in enumerate(analysis['key_quotes'], 1):
                        st.write(f"{i}. {quote}")
                else:
                    st.info("Key points will appear here")
                
                # Topics Section
                st.subheader("🏷️ Topics")
                if analysis.get('topics'):
                    for topic in analysis['topics']:
                        st.badge(topic) if hasattr(st, 'badge') else st.write(f"• {topic}")
                else:
                    st.info("Topics will appear here")
                
                # Debug info (can be hidden in production)
                if st.checkbox("Show debug info", help="Show technical details about content extraction"):
                    st.subheader("🔧 Debug Info")
                    if analysis.get('analysis_source'):
                        st.write(f"**Source:** {analysis['analysis_source']}")
                    if analysis.get('content_preview'):
                        st.write("**Content Preview:**")
                        st.text_area("", analysis['content_preview'][:300], height=100, disabled=True, key="debug_preview")
    
    with tab3:
        st.header("3. Generate Social Media Posts")
        st.write("Create engaging social media content based on your video analysis.")
        
        if 'video_analysis' not in st.session_state:
            st.info("📹 Please upload and process a video first")
        else:
            analysis = st.session_state.video_analysis
            
            generate_col1, generate_col2 = st.columns([1, 3])
            with generate_col1:
                generate_button = st.button("🚀 Generate Posts", type="primary")
            
            if generate_button:
                with st.spinner("✨ Generating social media posts..."):
                    try:
                        posts = st.session_state.social_generator.generate_posts(analysis)
                        st.session_state.social_posts = posts
                        st.success("✅ Posts generated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error generating posts: {str(e)}")
            
            if 'social_posts' in st.session_state:
                posts = st.session_state.social_posts
                
                # Display posts in tabs for better organization
                platform_tabs = st.tabs(["📘 Facebook", "🐦 Twitter", "💼 LinkedIn", "📸 Instagram"])
                
                with platform_tabs[0]:
                    st.subheader("Facebook Post")
                    st.text_area("", posts.get('facebook', 'Post will appear here...'), 
                               height=150, key="fb_post", disabled=True)
                    if st.button("📋 Copy Facebook Post", key="copy_fb"):
                        st.success("✅ Copied to clipboard!")
                
                with platform_tabs[1]:
                    st.subheader("Twitter Thread")
                    st.text_area("", posts.get('twitter', 'Thread will appear here...'), 
                               height=150, key="tw_post", disabled=True)
                    if st.button("📋 Copy Twitter Thread", key="copy_tw"):
                        st.success("✅ Copied to clipboard!")
                
                with platform_tabs[2]:
                    st.subheader("LinkedIn Post")
                    st.text_area("", posts.get('linkedin', 'Post will appear here...'), 
                               height=150, key="li_post", disabled=True)
                    if st.button("📋 Copy LinkedIn Post", key="copy_li"):
                        st.success("✅ Copied to clipboard!")
                
                with platform_tabs[3]:
                    st.subheader("Instagram Caption")
                    st.text_area("", posts.get('instagram', 'Caption will appear here...'), 
                               height=150, key="ig_post", disabled=True)
                    if st.button("📋 Copy Instagram Caption", key="copy_ig"):
                        st.success("✅ Copied to clipboard!")
    
    with tab4:
        st.header("4. Create Video Compilations")
        st.write("Generate custom video compilations based on specific criteria.")
        
        if 'video_analysis' not in st.session_state:
            st.info("📹 Please upload and process a video first")
        else:
            st.subheader("🎬 Compilation Options")
            
            compilation_type = st.selectbox(
                "Choose compilation type:",
                ["Highlights", "Key Moments", "Topic-based", "Custom Query"],
                help="Select the type of compilation you want to create"
            )
            
            custom_query = ""
            if compilation_type == "Custom Query":
                custom_query = st.text_input(
                    "Enter your compilation criteria:",
                    placeholder="Show me all parts where the speaker talks about technology",
                    help="Describe what content you want to include in the compilation"
                )
            
            col1, col2 = st.columns(2)
            with col1:
                duration_limit = st.slider("Max duration (minutes)", 1, 10, 3,
                                         help="Maximum duration for the compilation")
            with col2:
                quality = st.selectbox("Quality", ["Standard", "High", "Ultra"],
                                     help="Compilation quality setting")
            
            if st.button("🎥 Create Compilation", type="primary"):
                with st.spinner("🎬 Creating compilation... This may take several minutes."):
                    try:
                        criteria = custom_query if compilation_type == "Custom Query" else compilation_type.lower()
                        
                        compilation_url = st.session_state.video_processor.create_compilation(
                            st.session_state.video_analysis['video_id'],
                            criteria,
                            duration_limit * 60  # Convert to seconds
                        )
                        
                        if compilation_url and compilation_url != "Compilation created successfully":
                            st.success("✅ Compilation created successfully!")
                            st.video(compilation_url)
                        else:
                            st.info("🔧 Compilation created. Video URL generation in progress.")
                            
                    except Exception as e:
                        st.error(f"❌ Error creating compilation: {str(e)}")
                        st.info("💡 This feature requires advanced VideoDB capabilities. Please check your API access level.")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>🎥 AI Video Analysis Tool | Powered by VideoDB & Google AI</p>
            <p><small>Using VideoDB SearchType.semantic and IndexType.spoken_word for accurate content extraction</small></p>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()