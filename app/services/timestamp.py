import videodb
import os
from dotenv import load_dotenv
load_dotenv()


client =videodb.connect(api_key= os.getenv("VIDEODB_API_KEY"))

async def find_timestamps(query: str):
    # Returns list of {start, end, reason}
    results = client.search_topics(query)
    return [{
        "start": hit.start_time,
        "end": hit.end_time,
        "reason": hit.description
    } for hit in results]