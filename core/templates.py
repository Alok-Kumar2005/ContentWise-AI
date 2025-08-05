class Template:
    linkedin_template = """
            Create a professional LinkedIn post based on this video content.
            
            Video Summary: {summary}
            Key Topics: {topics}
            Video URL: {video_url}
            
            Requirements:
            - Professional tone
            - Engaging opening hook
            - Key insights from the video
            - Call to action
            - Relevant hashtags (3-5)
            - Maximum {max_length} characters
            
            Make it valuable for professional network.
            """
    
    twitter_template = """
            Create a Twitter thread (2-3 tweets) based on this video content.
            
            Video Summary: {summary}
            Key Topics: {topics}
            Video URL: {video_url}
            
            Requirements:
            - Casual, engaging tone
            - Hook in first tweet
            - Key insights in thread
            - Relevant hashtags (2-3 per tweet)
            - Each tweet max 280 characters
            
            Format as: Tweet 1/3: [content] \n Tweet 2/3: [content] etc.
            """
    
    instagram_template = """
            Create an Instagram post based on this video content.
            
            Video Summary: {summary}
            Key Topics: {topics}
            Video URL: {video_url}
            
            Requirements:
            - Engaging, visual storytelling tone
            - Compelling caption with emojis
            - Key insights from video
            - Story-like format
            - Relevant hashtags (5-10)
            - Maximum {max_length} characters
            
            Make it visually appealing and engaging."""
    
    facebook_template = """
            Create a Facebook post based on this video content.
            
            Video Summary: {summary}
            Key Topics: {topics}
            Video URL: {video_url}
            
            Requirements:
            - Friendly, conversational tone
            - Engaging story format
            - Key insights and takeaways
            - Questions to encourage engagement
            - Maximum {max_length} characters
            
            Make it shareable and discussion-worthy."""
    
    summary_template="""
            Create a comprehensive summary of this video content.
            
            Title: {title}
            Transcript: {transcript}
            
            Provide:
            1. Main topic and purpose
            2. Key points discussed (3-5 bullet points)
            3. Important insights or takeaways
            4. Target audience
            
            Keep the summary engaging and informative.
            """
    
    key_topic_template="""
            Analyze this video transcript and extract the main topics discussed.
            
            Transcript: {transcript}
            
            Return only the top 5-7 key topics as a comma-separated list.
            Focus on the most important and relevant topics.
            """
    rag_template="""You are an AI assistant helping users understand video content. Based on the provided context from the video transcript, answer the user's question accurately and comprehensively.

Context from video transcript:
{context}

User Question: {question}

Instructions:
1. Answer based primarily on the provided context
2. Be specific and detailed in your response
3. If the context doesn't contain enough information, mention that clearly
4. Quote relevant parts from the transcript when appropriate
5. Keep your response focused and relevant to the question
6. If the question cannot be answered from the context, say so explicitly

Answer:"""

    quiz_template = """
    You are an expert quiz generator. Based on the following video transcript, create exactly {num_questions} multiple-choice questions that test understanding of the key concepts and information presented.

    Video Title: {title}
    Transcript: {transcript}

    Generate questions that:
    1. Cover the most important topics discussed
    2. Test comprehension and understanding
    3. Are clear and unambiguous
    4. Have exactly 4 options each
    5. Have only one correct answer
    6. Vary in difficulty from basic recall to analytical thinking

    Format your response EXACTLY like this example:

    QUESTION 1: What is the main topic discussed in the video?
    A) Option 1
    B) Option 2
    C) Option 3
    D) Option 4
    CORRECT: A

    QUESTION 2: Which concept was explained first?
    A) Option 1
    B) Option 2
    C) Option 3
    D) Option 4
    CORRECT: B

    Continue this format for all {num_questions} questions. Make sure each question is numbered sequentially and follows the exact format above.
    
    Important guidelines:
    - Questions should be based directly on content from the transcript
    - Avoid trick questions or overly complex wording
    - Make incorrect options plausible but clearly wrong
    - Ensure questions test different aspects of the content
    - Include a mix of factual recall and conceptual understanding questions
    """