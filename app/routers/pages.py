from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/video-chat", response_class=HTMLResponse)
async def get_video_chat(request: Request):
    return templates.TemplateResponse("video_chat.html", {"request": request})


@router.get("/text-chat", response_class=HTMLResponse)
async def get_text_chat(request: Request):
    return templates.TemplateResponse("text_chat.html", {"request": request})
