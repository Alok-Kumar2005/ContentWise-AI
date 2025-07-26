import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings, GoogleGenerativeAI
import videodb
import os
from dotenv import load_dotenv
load_dotenv()


VIDEO_DB_API_KEY = os.getenv("VIDEODB_API_KEY")

def get_videodb_client():
    return videodb.connect(api_key= os.getenv("VIDEODB_API_KEY"))

async def analyze_video(file, url):
    client = get_videodb_client()
    # ingest
    if file:
        res = client.ingest(file.file)
    else:
        res = client.ingest_url(url)

    # extract transcript / comments / metadata
    transcript = res.transcript
    comments = res.comments

    # Summarize transcript and sentiment
    llm = GoogleGenerativeAI()
    summary = llm.predict(f"Summarize this transcript: {transcript}")

    # Key quotes & topics
    quotes = llm.predict(f"Extract key quotes from: {transcript}").split("\n")
    topics = llm.predict(f"List main topics: {transcript}").split(",")

    # Forecast comment count over time
    forecast = client.forecast_comments(res.video_id)

    return summary, quotes, topics, forecast