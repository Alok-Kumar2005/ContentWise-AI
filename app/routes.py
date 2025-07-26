from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.schemas.models import AnalysisResponse
from app.services.video_analysis import analyze_video
from app.services.summarizer import generate_social_posts
from app.services.timestamp import find_timestamps

router = APIRouter(prefix="/api", tags=["analysis"])

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    file: UploadFile = File(None),
    url: str = Form(""),
    query: str = Form("")
):
    if not file and not url:
        raise HTTPException(status_code=400, detail="Provide a file or a URL.")

    # 1. Video analysis
    summary, quotes, topics, forecast = await analyze_video(file, url)

    # 2. Social media posts
    posts = await generate_social_posts(summary)

    # 3. Timestamp snippets (optional)
    snippets = []
    if query:
        snippets = await find_timestamps(query)

    return AnalysisResponse(
        summary=summary,
        key_quotes=quotes,
        topics=topics,
        forecast=forecast,
        posts=posts,
        snippets=snippets,
    )