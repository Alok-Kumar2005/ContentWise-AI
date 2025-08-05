import streamlit as st
import os
from datetime import datetime
import logging
import atexit
import asyncio
import threading
import time

from services.videodb_service import VideoDBService
from services.llm_service import LLMService
from services.social_media_generator import SocialMediaGenerator
from services.rag_service import RAGService
from services.quiz_generator  import QuizGeneratorService
from models.video_processor import VideoAnalysis, TimestampQuery, Quiz, QuizQuestion
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
        services['quiz_generator'] = QuizGeneratorService()
        logging.info("Core services initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing services: {e}")
        raise
    return services

def init_rag_service():
    """Initialize RAG service for the session with proper error handling"""
    try:
        # Ensure we have an event loop in the current thread
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Create RAG service with timeout
        rag_service = RAGService()
        
        # Verify the service was initialized properly
        if hasattr(rag_service, 'client') and rag_service.client is not None:
            logging.info("RAG service initialized successfully")
            return rag_service
        else:
            logging.error("RAG service initialization failed - client not created")
            return None
            
    except Exception as e:
        logging.error(f"Error initializing RAG service: {e}")
        return None

# Cleanup function for when the app closes
def cleanup_rag():
    """Clean up RAG service when app closes"""
    try:
        if 'rag_service' in st.session_state and st.session_state.rag_service:
            st.session_state.rag_service.cleanup_safely()
            logging.info("RAG service cleaned up on exit")
    except Exception as e:
        logging.error(f"Error during RAG cleanup: {e}")

# Register cleanup function
atexit.register(cleanup_rag)

def safe_rag_operation(operation_func, *args, **kwargs):
    """Safely execute RAG operations with error handling"""
    try:
        if 'rag_service' not in st.session_state or not st.session_state.rag_service:
            return None, "RAG service not initialized"
        
        result = operation_func(*args, **kwargs)
        return result, None
    except Exception as e:
        error_msg = f"RAG operation failed: {str(e)}"
        logging.error(error_msg)
        return None, error_msg

def render_quiz_interface(quiz, services):
    """Render the quiz taking interface"""
    st.subheader(f"📝 {quiz.title}")
    st.markdown(f"**Total Questions:** {quiz.total_questions}")
    st.markdown("---")
    
    # Initialize session state for quiz answers
    if 'quiz_answers' not in st.session_state:
        st.session_state.quiz_answers = {}
    
    # Display questions
    for i, question in enumerate(quiz.questions):
        st.markdown(f"**Question {i+1}:** {question.question}")
        
        # Radio button for options
        option_key = f"question_{i}"
        selected_option = st.radio(
            f"Choose your answer for Question {i+1}:",
            options=list(range(len(question.options))),
            format_func=lambda x: f"{chr(65+x)}) {question.options[x]}",
            key=option_key,
            index=None
        )
        
        # Store answer in session state
        if selected_option is not None:
            st.session_state.quiz_answers[str(i)] = selected_option
        
        st.markdown("---")
    
    # Submit quiz button
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("📊 Submit Quiz", type="primary"):
            if len(st.session_state.quiz_answers) == len(quiz.questions):
                # Calculate score
                score_result = services['quiz_generator'].calculate_score(
                    st.session_state.quiz_answers, 
                    quiz
                )
                
                # Store results
                st.session_state.quiz_results = score_result
                st.session_state.quiz_submitted = True
                st.rerun()
            else:
                st.error("Please answer all questions before submitting!")

def render_quiz_results(quiz_results):
    """Render quiz results"""
    st.subheader("🎯 Quiz Results")
    
    # Score summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Score", f"{quiz_results['score']}/{quiz_results['total']}")
    
    with col2:
        st.metric("Percentage", f"{quiz_results['percentage']}%")
    
    with col3:
        status = "✅ PASSED" if quiz_results['passed'] else "❌ FAILED"
        st.metric("Status", status)
    
    with col4:
        if quiz_results['percentage'] >= 80:
            grade = "A"
        elif quiz_results['percentage'] >= 60:
            grade = "B"
        elif quiz_results['percentage'] >= 40:
            grade = "C"
        else:
            grade = "F"
        st.metric("Grade", grade)
    
    # Progress bar
    st.progress(quiz_results['percentage'] / 100)
    
    # Detailed results
    st.markdown("---")
    st.subheader("📋 Detailed Results")
    
    for result in quiz_results['results']:
        question_num = result['question_index'] + 1
        is_correct = result['is_correct']
        
        # Question header with result
        status_emoji = "✅" if is_correct else "❌"
        st.markdown(f"**{status_emoji} Question {question_num}:** {result['question']}")
        
        # Show options with highlighting
        for i, option in enumerate(result['options']):
            option_letter = chr(65 + i)
            
            if i == result['correct_answer']:
                # Correct answer
                st.markdown(f"🟢 **{option_letter}) {option}** ← Correct Answer")
            elif i == result['user_answer']:
                # User's wrong answer
                st.markdown(f"🔴 **{option_letter}) {option}** ← Your Answer")
            else:
                # Other options
                st.markdown(f"⚪ {option_letter}) {option}")
        
        st.markdown("---")
    
    # Reset quiz button
    if st.button("🔄 Take Quiz Again"):
        # Clear quiz session state
        for key in ['quiz_answers', 'quiz_results', 'quiz_submitted']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

def main():
    st.set_page_config(
        page_title="AI-Powered Video Analysis with RAG & Quiz",
        page_icon="🎥",
        layout="wide"
    )
    
    st.title("🎥 AI-Powered Video Analysis with RAG & Quiz")
    st.markdown("Upload your video or provide a URL to get AI-powered analysis, summaries, social media posts, intelligent Q&A, and take quizzes!")
    
    # Initialize services
    try:
        services = init_services()
        
        # Initialize RAG service for this session if not already done
        if 'rag_service' not in st.session_state:
            with st.spinner("Initializing RAG service..."):
                rag_service = init_rag_service()
                if rag_service:
                    st.session_state.rag_service = rag_service
                    st.success("✅ RAG service initialized successfully!")
                else:
                    st.warning("⚠️ RAG service initialization failed. Q&A functionality will be limited.")
                    st.session_state.rag_service = None
    except Exception as e:
        st.error(f"Error initializing services: {e}")
        st.stop()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        st.info("Make sure to set your API keys in environment variables:\n- VIDEODB_API_KEY\n- GOOGLE_API_KEY")
        
        # RAG Database Status
        if 'rag_service' in st.session_state and st.session_state.rag_service:
            try:
                stats = st.session_state.rag_service.get_database_stats()
                st.subheader("📊 RAG Database Status")
                st.write(f"**Status:** {stats['status']}")
                st.write(f"**Text Chunks:** {stats['chunks']}")
                st.write(f"**Session ID:** {stats.get('session_id', 'Unknown')[:8]}...")
                
                if st.button("🗑️ Clear RAG Database"):
                    try:
                        with st.spinner("Clearing RAG database..."):
                            st.session_state.rag_service.cleanup_safely()
                            time.sleep(1)  # Give time for cleanup
                            
                            new_rag_service = init_rag_service()
                            if new_rag_service:
                                st.session_state.rag_service = new_rag_service
                                st.success("✅ RAG database cleared and reinitialized!")
                            else:
                                st.error("❌ Failed to reinitialize RAG service")
                                st.session_state.rag_service = None
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing RAG database: {e}")
                        
            except Exception as e:
                st.error(f"Error getting RAG status: {e}")
                st.subheader("📊 RAG Database Status")
                st.write("**Status:** Error")
        else:
            st.subheader("📊 RAG Database Status")
            st.write("**Status:** Not initialized")
            if st.button("🔄 Initialize RAG Service"):
                with st.spinner("Initializing RAG service..."):
                    rag_service = init_rag_service()
                    if rag_service:
                        st.session_state.rag_service = rag_service
                        st.success("✅ RAG service initialized!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to initialize RAG service")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📤 Upload & Analyze", 
        "📝 Summary & Topics", 
        "📱 Social Media Posts", 
        "🔍 Timestamp Search",
        "🤖 AI Q&A (RAG)",
        "🧠 Quiz Generator"
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
                        rag_success = False
                        if 'rag_service' in st.session_state and st.session_state.rag_service:
                            try:
                                with st.spinner("Creating RAG database..."):
                                    result, error = safe_rag_operation(
                                        st.session_state.rag_service.create_vector_database,
                                        transcript, 
                                        st.session_state.get('video_title', '')
                                    )
                                    rag_success = result if result is not None else False
                                    if error:
                                        st.warning(f"RAG database creation issue: {error}")
                            except Exception as e:
                                st.warning(f"RAG database creation failed: {e}")
                                rag_success = False
                        else:
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
                            st.text_area("Transcript", transcript, height=300, disabled=True)
                        
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
            try:
                stats = st.session_state.rag_service.get_database_stats()
                
                if stats['chunks'] > 0:
                    st.success(f"✅ RAG database ready with {stats['chunks']} text chunks")
                    
                    # Advanced options
                    with st.expander("🔧 Advanced Options"):
                        col1, col2 = st.columns(2)
                        with col1:
                            show_sources = st.checkbox("Show sources in responses", value=False)
                            temperature = st.slider("Response creativity", 0.0, 1.0, 0.7, 0.1)
                        with col2:
                            num_chunks = st.slider("Number of chunks to retrieve", 1, 10, 5)
                            
                        if st.button("🔄 Update RAG Parameters"):
                            result, error = safe_rag_operation(
                                st.session_state.rag_service.update_chain_parameters,
                                temperature=temperature,
                                k=num_chunks
                            )
                            if error:
                                st.error(f"Error updating parameters: {error}")
                            else:
                                st.success("✅ RAG parameters updated!")
                    
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
                                    # Get show_sources value from advanced options
                                    show_sources_val = False
                                    try:
                                        # Check if advanced options are expanded and get the value
                                        show_sources_val = show_sources if 'show_sources' in locals() else False
                                    except:
                                        show_sources_val = False
                                    
                                    result, error = safe_rag_operation(
                                        st.session_state.rag_service.query_video_content,
                                        prompt,
                                        return_sources=show_sources_val
                                    )
                                    
                                    if error:
                                        response = f"❌ Error generating response: {error}"
                                        st.error(response)
                                    else:
                                        response = result if result else "No response generated."
                                        st.markdown(response)
                                    
                                    # Add assistant response to chat history
                                    st.session_state.rag_messages.append({"role": "assistant", "content": response})
                                    
                                except Exception as e:
                                    error_msg = f"❌ Unexpected error: {str(e)}"
                                    st.error(error_msg)
                                    st.session_state.rag_messages.append({"role": "assistant", "content": error_msg})
                    
                    # Chat management buttons
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("🗑️ Clear Chat History"):
                            st.session_state.rag_messages = []
                            st.rerun()
                    
                    with col2:
                        if st.button("📊 Get Similar Chunks"):
                            if st.session_state.rag_messages:
                                last_user_message = None
                                for msg in reversed(st.session_state.rag_messages):
                                    if msg["role"] == "user":
                                        last_user_message = msg["content"]
                                        break
                                
                                if last_user_message:
                                    result, error = safe_rag_operation(
                                        st.session_state.rag_service.get_similar_chunks,
                                        last_user_message,
                                        k=3
                                    )
                                    if error:
                                        st.error(f"Error getting similar chunks: {error}")
                                    else:
                                        st.subheader("📄 Similar Text Chunks")
                                        st.text_area("Similar chunks", result, height=300, disabled=True)
                                else:
                                    st.info("No user messages found to search for similar chunks.")
                            else:
                                st.info("Ask a question first to find similar chunks.")
                    
                    with col3:
                        if st.button("📈 Database Stats"):
                            try:
                                stats = st.session_state.rag_service.get_database_stats()
                                st.json(stats)
                            except Exception as e:
                                st.error(f"Error getting stats: {e}")
                    
                else:
                    st.info("Please upload and analyze a video first to enable Q&A functionality.")
                    st.markdown("**Steps:**")
                    st.markdown("1. Go to 'Upload & Analyze' tab")
                    st.markdown("2. Upload a video or provide a URL")
                    st.markdown("3. Click 'Analyze Video'")
                    st.markdown("4. Go to 'Summary & Topics' and click 'Generate Summary'")
                    st.markdown("5. Return here to ask questions!")
                    
            except Exception as e:
                st.error(f"Error with RAG interface: {e}")
                st.info("Try reinitializing the RAG service from the sidebar.")
                
        else:
            st.error("❌ RAG service not initialized properly")
            st.markdown("The RAG service failed to initialize. This could be due to:")
            st.markdown("- Missing API keys (check environment variables)")
            st.markdown("- Network connectivity issues")
            st.markdown("- Dependency conflicts")
            
            if st.button("🔄 Try to Initialize RAG Service"):
                with st.spinner("Attempting to initialize RAG service..."):
                    rag_service = init_rag_service()
                    if rag_service:
                        st.session_state.rag_service = rag_service
                        st.success("✅ RAG service initialized!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to initialize RAG service. Check logs for details.")
    
    with tab6:
        st.header("6. 🧠 Quiz Generator")
        st.markdown("Generate and take a quiz based on the video content to test your understanding!")
        
        if 'transcript' in st.session_state:
            # Check if quiz already exists and hasn't been submitted
            if 'current_quiz' not in st.session_state or st.button("🔄 Generate New Quiz"):
                # Clear any existing quiz state
                for key in ['current_quiz', 'quiz_answers', 'quiz_results', 'quiz_submitted']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                with st.spinner("🧠 Generating quiz from video content..."):
                    try:
                        # Generate quiz from transcript
                        quiz = services['quiz_generator'].generate_quiz(
                            st.session_state.transcript,
                            st.session_state.get('video_title', 'Video Content'),
                            num_questions=5
                        )
                        
                        st.session_state.current_quiz = quiz
                        st.session_state.quiz_submitted = False
                        st.success(f"✅ Quiz generated with {quiz.total_questions} questions!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error generating quiz: {e}")
                        logging.error(f"Quiz generation error: {e}")
            
            # Display quiz or results
            if 'current_quiz' in st.session_state:
                quiz = st.session_state.current_quiz
                
                # Show quiz results if submitted
                if st.session_state.get('quiz_submitted', False) and 'quiz_results' in st.session_state:
                    render_quiz_results(st.session_state.quiz_results)
                else:
                    # Show quiz interface
                    render_quiz_interface(quiz, services)
                
                # Quiz Statistics (if results exist)
                if 'quiz_results' in st.session_state:
                    st.markdown("---")
                    st.subheader("📈 Performance Analytics")
                    
                    results = st.session_state.quiz_results
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Question-wise Performance:**")
                        for i, result in enumerate(results['results']):
                            status = "✅" if result['is_correct'] else "❌"
                            st.write(f"Question {i+1}: {status}")
                    
                    with col2:
                        st.markdown("**Difficulty Analysis:**")
                        if results['percentage'] >= 80:
                            st.success("🌟 Excellent understanding!")
                        elif results['percentage'] >= 60:
                            st.info("👍 Good grasp of the content!")
                        elif results['percentage'] >= 40:
                            st.warning("📚 Consider reviewing the material")
                        else:
                            st.error("📖 Recommend watching the video again")
            
            else:
                st.info("Click 'Generate New Quiz' to create a quiz from the video content.")
        
        else:
            st.info("Please upload and analyze a video first to generate a quiz.")
            st.markdown("**Steps to generate a quiz:**")
            st.markdown("1. Go to 'Upload & Analyze' tab and upload a video")
            st.markdown("2. Go to 'Summary & Topics' tab and generate summary")
            st.markdown("3. Return here to generate and take a quiz!")
            
            # Show sample quiz preview
            with st.expander("📋 See Quiz Preview"):
                st.markdown("**Sample Question Format:**")
                st.markdown("**Question 1:** What is the main topic discussed in the video?")
                st.markdown("A) Option 1")
                st.markdown("B) Option 2") 
                st.markdown("C) Option 3")
                st.markdown("D) Option 4")
                st.markdown("")
                st.markdown("**Features:**")
                st.markdown("- 5 multiple-choice questions")
                st.markdown("- 4 options per question")
                st.markdown("- Instant scoring and feedback")
                st.markdown("- Detailed answer explanations")
                st.markdown("- Performance analytics")

if __name__ == "__main__":
    main()