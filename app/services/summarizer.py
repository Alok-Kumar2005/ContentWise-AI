from langchain_google_genai import ChatGoogleGenerativeAI
from app.schemas.models import SocialPosts
import os
from dotenv import load_dotenv
load_dotenv()

async def generate_social_posts(summary: str) -> SocialPosts:
    llm = ChatGoogleGenerativeAI(model = "gemini-1.5-flash" , google_api_key = os.getenv("GOOGLE_API_KEY"))
    return SocialPosts(
        linkedin=llm.predict(f"Write a LinkedIn post about: {summary}"),
        twitter=llm.predict(f"Write a tweet about: {summary}"),
        facebook=llm.predict(f"Write a Facebook post about: {summary}"),
        instagram=llm.predict(f"Write an Instagram caption about: {summary}"),
    )