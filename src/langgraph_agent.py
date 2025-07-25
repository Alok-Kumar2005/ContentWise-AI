from langgraph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from typing import Dict, Any, List
import json
from src.utils.config import Config

class VideoAnalysisState:
    """State management for video analysis workflow"""
    def __init__(self):
        self.video_id: str = ""
        self.transcript: str = ""
        self.summary: str = ""
        self.topics: List[str] = []
        self.key_quotes: List[str] = []
        self.social_posts: Dict[str, str] = {}
        self.user_query: str = ""
        self.query_response: str = ""
        self.timestamps: List[Dict] = []
        self.current_step: str = "start"
        self.error: str = ""

class VideoAnalysisAgent:
    """LangGraph-based agent for comprehensive video analysis"""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model = "gemini-1.5-flash" , google_api_key = Config.GOOGLE_API_KEY )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(VideoAnalysisState)
        
        # Add nodes
        workflow.add_node("analyze_content", self._analyze_content)
        workflow.add_node("generate_social_posts", self._generate_social_posts)
        workflow.add_node("handle_query", self._handle_query)
        workflow.add_node("error_handler", self._handle_error)
        
        # Add edges
        workflow.add_edge("analyze_content", "generate_social_posts")
        workflow.add_edge("generate_social_posts", END)
        workflow.add_edge("handle_query", END)
        workflow.add_edge("error_handler", END)
        
        # Set entry point
        workflow.set_entry_point("analyze_content")
        
        return workflow.compile()
    
    def _analyze_content(self, state: VideoAnalysisState) -> VideoAnalysisState:
        """Analyze video content and extract insights"""
        try:
            analysis_prompt = PromptTemplate(
                input_variables=["transcript"],
                template="""
                Analyze the following video transcript and provide:
                1. A comprehensive summary (3-4 sentences)
                2. Key topics discussed (5-7 topics)
                3. Important quotes or statements (5-8 quotes)
                4. Sentiment analysis
                5. Target audience identification
                
                Transcript: {transcript}
                
                Return your analysis in the following JSON format:
                {{
                    "summary": "...",
                    "topics": ["topic1", "topic2", ...],
                    "key_quotes": ["quote1", "quote2", ...],
                    "sentiment": "positive/negative/neutral",
                    "target_audience": "..."
                }}
                """
            )
            
            chain = LLMChain(llm=self.llm, prompt=analysis_prompt)
            result = chain.run(transcript=state.transcript[:4000])
            
            # Parse JSON result
            try:
                analysis = json.loads(result)
                state.summary = analysis.get("summary", "")
                state.topics = analysis.get("topics", [])
                state.key_quotes = analysis.get("key_quotes", [])
                state.sentiment = analysis.get("sentiment", "neutral")
                state.target_audience = analysis.get("target_audience", "")
            except json.JSONDecodeError:
                # Fallback parsing if JSON fails
                state = self._fallback_parse(result, state)
            
            state.current_step = "content_analyzed"
            
        except Exception as e:
            state.error = f"Content analysis error: {str(e)}"
            state.current_step = "error"
        
        return state
    
    def _generate_social_posts(self, state: VideoAnalysisState) -> VideoAnalysisState:
        """Generate social media posts for all platforms"""
        try:
            platforms = ["facebook", "twitter", "linkedin", "instagram"]
            
            for platform in platforms:
                post_prompt = PromptTemplate(
                    input_variables=["platform", "summary", "topics", "quotes", "audience"],
                    template="""
                    Create an engaging {platform} post based on:
                    Summary: {summary}
                    Topics: {topics}
                    Key Quotes: {quotes}
                    Target Audience: {audience}
                    
                    Platform-specific requirements:
                    - Facebook: Conversational, 100-200 words, emojis, engagement question
                    - Twitter: Thread format, max 280 chars per tweet, hashtags
                    - LinkedIn: Professional, 150-300 words, industry insights
                    - Instagram: Visual focus, emojis, aesthetic appeal, 100-150 words
                    
                    Post:
                    """
                )
                
                chain = LLMChain(llm=self.llm, prompt=post_prompt)
                post = chain.run(
                    platform=platform,
                    summary=state.summary,
                    topics=", ".join(state.topics[:5]),
                    quotes=", ".join(state.key_quotes[:3]),
                    audience=getattr(state, 'target_audience', 'general audience')
                )
                
                state.social_posts[platform] = post.strip()
            
            state.current_step = "posts_generated"
            
        except Exception as e:
            state.error = f"Social media generation error: {str(e)}"
            state.current_step = "error"
        
        return state
    
    def _handle_query(self, state: VideoAnalysisState) -> VideoAnalysisState:
        """Handle user queries about the video"""
        try:
            query_prompt = PromptTemplate(
                input_variables=["query", "transcript", "summary", "topics"],
                template="""
                Answer the user's question about the video based on the available information.
                
                Question: {query}
                Video Summary: {summary}
                Topics: {topics}
                Transcript (partial): {transcript}
                
                Provide a detailed answer and if possible, mention relevant timestamps or sections.
                If you cannot answer the question based on the available information, say so clearly.
                
                Answer:
                """
            )
            
            chain = LLMChain(llm=self.llm, prompt=query_prompt)
            response = chain.run(
                query=state.user_query,
                transcript=state.transcript[:3000],
                summary=state.summary,
                topics=", ".join(state.topics)
            )
            
            state.query_response = response.strip()
            state.current_step = "query_handled"
            
        except Exception as e:
            state.error = f"Query handling error: {str(e)}"
            state.current_step = "error"
        
        return state
    
    def _handle_error(self, state: VideoAnalysisState) -> VideoAnalysisState:
        """Handle any errors that occur during processing"""
        state.current_step = "error_handled"
        return state
    
    def _fallback_parse(self, result: str, state: VideoAnalysisState) -> VideoAnalysisState:
        """Fallback parsing when JSON parsing fails"""
        lines = result.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'summary' in line.lower():
                state.summary = line.split(':', 1)[-1].strip().strip('"')
            elif 'topics' in line.lower():
                topics_str = line.split(':', 1)[-1].strip()
                state.topics = [t.strip().strip('"') for t in topics_str.split(',') if t.strip()]
            elif 'quotes' in line.lower():
                quotes_str = line.split(':', 1)[-1].strip()
                state.key_quotes = [q.strip().strip('"') for q in quotes_str.split(',') if q.strip()]
        
        return state
    
    def process_video(self, video_id: str, transcript: str) -> VideoAnalysisState:
        """Process video through the complete workflow"""
        state = VideoAnalysisState()
        state.video_id = video_id
        state.transcript = transcript
        
        # Run the graph
        final_state = self.graph.invoke(state)
        return final_state
    
    def handle_user_query(self, state: VideoAnalysisState, query: str) -> VideoAnalysisState:
        """Handle a specific user query"""
        state.user_query = query
        state.current_step = "handle_query"
        
        # Process query
        updated_state = self._handle_query(state)
        return updated_state