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