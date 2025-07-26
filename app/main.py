from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .routes import router

app = FastAPI(title="Video AI Assistant")
app.include_router(router)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", include_in_schema=False)
async def home(request):
    return templates.TemplateResponse("index.html", {"request": request})