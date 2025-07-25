class PromptTemplates:
    """Collection of prompt templates for different tasks"""
    
    VIDEO_ANALYSIS = """
    Analyze the following video transcript and provide comprehensive insights:
    
    Transcript: {transcript}
    Title: {title}
    Description: {description}
    
    Please provide:
    1. Executive Summary (2-3 sentences)
    2. Key Topics (5-7 main topics discussed)
    3. Important Quotes (5-8 notable statements)
    4. Sentiment Analysis (overall tone)
    5. Target Audience
    6. Action Items or Key Takeaways
    
    Format as JSON:
    {{
        "summary": "...",
        "topics": ["topic1", "topic2", ...],
        "key_quotes": ["quote1", "quote2", ...],
        "sentiment": "positive/negative/neutral",
        "target_audience": "...",
        "takeaways": ["takeaway1", "takeaway2", ...]
    }}
    """
    
    FACEBOOK_POST = """
    Create an engaging Facebook post based on this video content:
    
    Summary: {summary}
    Topics: {topics}
    Key Quotes: {quotes}
    Target Audience: {audience}
    
    Requirements:
    - Conversational and friendly tone
    - 100-200 words
    - Include relevant emojis
    - Ask an engaging question
    - Add 3-5 relevant hashtags
    - Encourage shares and comments
    
    Facebook Post:
    """
    
    TWITTER_THREAD = """
    Create a Twitter thread (3-4 tweets) based on this video content:
    
    Summary: {summary}
    Topics: {topics}
    Key Quotes: {quotes}
    
    Requirements:
    - Each tweet max 280 characters
    - Number tweets (1/4, 2/4, etc.)
    - Include relevant hashtags and emojis
    - Make it shareable and engaging
    - End with a call-to-action
    
    Twitter Thread:
    """
    
    LINKEDIN_POST = """
    Create a professional LinkedIn post based on this video content:
    
    Summary: {summary}
    Topics: {topics}
    Key Quotes: {quotes}
    Target Audience: {audience}
    
    Requirements:
    - Professional and insightful tone
    - 150-300 words
    - Include industry insights
    - Add professional hashtags
    - Encourage meaningful discussion
    - Share key learnings or takeaways
    
    LinkedIn Post:
    """
    
    INSTAGRAM_POST = """
    Create an Instagram post based on this video content:
    
    Summary: {summary}
    Topics: {topics}
    Visual Elements: {visual_suggestions}
    
    Requirements:
    - Visual and aesthetic focus
    - 100-150 words
    - Include emojis throughout
    - Suggest visual elements in [brackets]
    - Use trending hashtags (8-12)
    - Inspiring and engaging tone
    
    Instagram Post:
    """
    
    QUERY_RESPONSE = """
    Answer the user's question about this video:
    
    Question: {query}
    Video Summary: {summary}
    Topics Covered: {topics}
    Available Transcript: {transcript}
    
    Instructions:
    - Provide a detailed, accurate answer
    - Reference specific parts of the video when possible
    - If timestamps are available, include them
    - If the question cannot be answered from the content, say so clearly
    - Be conversational and helpful
    
    Answer:
    """