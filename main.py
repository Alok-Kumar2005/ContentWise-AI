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
        videodb_api_key = st.text_input("VideoDB API Key", type="password")
        openai_api_key = st.text_input("GOOGLE_API_KEY", type="password")
        
        if videodb_api_key and openai_api_key:
            Config.VIDEODB_API_KEY = videodb_api_key
            Config.GOOGLE_API_KEY = openai_api_key
            os.environ["GOOGLE_API_KEY"] = openai_api_key
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 Upload Content", 
        "🤖 AI Analysis", 
        "📱 Social Media Posts", 
        "🎬 Video Compilations"
    ])
    
    with tab1:
        st.header("1. Provide Your Content")
        
        # Video upload options
        upload_option = st.radio(
            "Choose upload method:",
            ["Upload Video File", "Enter Video URL"]
        )
        
        video_url = None
        uploaded_file = None
        
        if upload_option == "Upload Video File":
            uploaded_file = st.file_uploader(
                "Choose a video file",
                type=['mp4', 'avi', 'mov', 'mkv'],
                help="Upload your video file (max 200MB)"
            )
        else:
            video_url = st.text_input(
                "Enter video URL:",
                placeholder="https://www.youtube.com/watch?v=..."
            )
        
        # Video metadata
        st.subheader("Video Information")
        video_title = st.text_input("Video Title (Optional)")
        video_description = st.text_area(
            "Video Description (Optional)",
            placeholder="A short description of what the video is about..."
        )
        
        # Process video button
        if st.button("🔍 Analyze Video", type="primary"):
            if not (videodb_api_key and openai_api_key):
                st.error("Please provide both VideoDB and OpenAI API keys in the sidebar")
            elif uploaded_file or video_url:
                with st.spinner("Processing video..."):
                    try:
                        result = st.session_state.video_processor.process_video(
                            uploaded_file=uploaded_file,
                            video_url=video_url,
                            title=video_title,
                            description=video_description
                        )
                        st.session_state.video_analysis = result
                        st.success("Video processed successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error processing video: {str(e)}")
            else:
                st.warning("Please upload a video file or enter a video URL")
    
    with tab2:
        st.header("2. AI-Powered Analysis")
        
        if 'video_analysis' not in st.session_state:
            st.info("Please upload and process a video first")
        else:
            analysis = st.session_state.video_analysis
            
            # Summary Section
            st.subheader("📝 Summary")
            if analysis.get('summary'):
                st.write(analysis['summary'])
            
            # Key Quotes Section
            st.subheader("💬 Key Quotes")
            if analysis.get('key_quotes'):
                for i, quote in enumerate(analysis['key_quotes'], 1):
                    st.write(f"{i}. \"{quote}\"")
            
            # Topics Section
            st.subheader("🏷️ Topics")
            if analysis.get('topics'):
                cols = st.columns(3)
                for i, topic in enumerate(analysis['topics']):
                    with cols[i % 3]:
                        st.metric("Topic", topic)
            
            # Query Section
            st.subheader("🔍 Ask Questions About the Video")
            user_query = st.text_input(
                "Enter your question:",
                placeholder="What is the main topic discussed in the video?"
            )
            
            if st.button("Get Answer") and user_query:
                with st.spinner("Finding answer..."):
                    try:
                        answer = st.session_state.video_processor.query_video(
                            user_query, analysis['video_id']
                        )
                        st.write("**Answer:**", answer['response'])
                        if answer.get('timestamps'):
                            st.write("**Relevant timestamps:**")
                            for ts in answer['timestamps']:
                                st.write(f"- {ts['start']}s - {ts['end']}s: {ts['content']}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with tab3:
        st.header("3. Generate Social Media Posts")
        
        if 'video_analysis' not in st.session_state:
            st.info("Please upload and process a video first")
        else:
            analysis = st.session_state.video_analysis
            
            if st.button("🚀 Generate Social Media Posts"):
                with st.spinner("Generating posts..."):
                    try:
                        posts = st.session_state.social_generator.generate_posts(analysis)
                        st.session_state.social_posts = posts
                        st.success("Posts generated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating posts: {str(e)}")
            
            if 'social_posts' in st.session_state:
                posts = st.session_state.social_posts
                
                # Display posts in columns
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📘 Facebook")
                    st.text_area("Facebook Post", posts.get('facebook', ''), height=100)
                    
                    st.subheader("🐦 Twitter")
                    st.text_area("Twitter Post", posts.get('twitter', ''), height=100)
                
                with col2:
                    st.subheader("💼 LinkedIn")
                    st.text_area("LinkedIn Post", posts.get('linkedin', ''), height=100)
                    
                    st.subheader("📸 Instagram")
                    st.text_area("Instagram Post", posts.get('instagram', ''), height=100)
    
    with tab4:
        st.header("4. Create Video Compilations")
        
        if 'video_analysis' not in st.session_state:
            st.info("Please upload and process a video first")
        else:
            st.subheader("🎬 Compilation Options")
            
            compilation_type = st.selectbox(
                "Choose compilation type:",
                ["Highlights", "Key Moments", "Topic-based", "Custom Query"]
            )
            
            if compilation_type == "Custom Query":
                custom_query = st.text_input(
                    "Enter your compilation criteria:",
                    placeholder="Show me all parts where the speaker talks about technology"
                )
            
            duration_limit = st.slider("Max duration (minutes)", 1, 10, 3)
            
            if st.button("🎥 Create Compilation"):
                with st.spinner("Creating compilation..."):
                    try:
                        # This would integrate with VideoDB's compilation features
                        st.info("Compilation feature will be implemented with VideoDB's video editing capabilities")
                        # compilation_url = create_compilation(...)
                        # st.video(compilation_url)
                    except Exception as e:
                        st.error(f"Error creating compilation: {str(e)}")

if __name__ == "__main__":
    main()