import os
import textwrap
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from . import database, schemas, services

load_dotenv()

database.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

@app.post("/api/users")
async def create_user(user: schemas.UserCreate, db: Session = Depends(services.get_db)):
    db_user = await services.get_user_by_email(user.email, db)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already in use")

    user = await services.create_user(user, db)
    return await services.create_token(user)


@app.post("/api/token")
async def generate_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(services.get_db)):
    user = await services.authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid Credentials"
        )

    return await services.create_token(user)


@app.get("/api/users/my-profile")
async def get_user(user: schemas.User = Depends(services.get_user_by_token)):
    return user

@app.post("/api/youtube-videos")
async def get_youtube_videos(search_params: dict, user: schemas.User = Depends(services.get_user_by_token)):
        
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

    default_search_params = {
        "q": "",
        "type": "video",
        "part": "id,snippet",
        "order": "viewCount",
        "videoCaption": "closedCaption",
        "videoDuration": "medium",
        "maxResults": 10,
        "publishedAfter": (datetime.now() - timedelta(days=7)).isoformat() + "Z",
    }

    q = search_params.get("q")

    if not q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parameter 'q' is required and must not be blank."
        )

    default_search_params.update(search_params)

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        response = youtube.search().list(**default_search_params).execute()
        video_ids = [video["id"]["videoId"] for video in response["items"]]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve YouTube videos"
        )

    return {
        "video_ids": video_ids
    }



@app.post("/api/transcript/{video_id}")
async def get_video_transcript(video_id: str, user: schemas.User = Depends(services.get_user_by_token)):

    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    formatter = TextFormatter()
    formatted_transcript = formatter.format_transcript(transcript)
    
    def remove_bracket_content(text):
        import re
        pattern = r'\[.*?\]'  # Regular expression pattern to match content within square brackets
        clean_text = re.sub(pattern, '', text)  # Replace the matched patterns with an empty string
        clean_text = re.sub(r'\n+', ' ', clean_text) 
        return clean_text
    
    formatted_transcript = remove_bracket_content(formatted_transcript)

    return {
        "video_id": video_id,
        "transcript": formatted_transcript
    }


@app.post("/api/summarize-transcript")
async def generate_summaries(transcript: schemas.Transcript, user: schemas.User = Depends(services.get_user_by_token)):

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    transcript_text = transcript.transcript.strip()

    if not transcript_text:
        raise HTTPException(
            status_code=400, detail="Transcript cannot be blank."
        )

    chunk_size = 1200 if len(transcript_text) >= 2500 else 2000

    chunks = textwrap.wrap(transcript_text, chunk_size)

    summaries = []

    for chunk in chunks:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a chef."},
                {"role": "user", "content": f"I want to create a Medium article based on several chunks I am sending. I'd like you to analyze it and make a recipe for users. Please respond with a raw markdown format. Here's the text: {chunk}"}
            ],
            "temperature": 0.5,
            "max_tokens": 1500,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions", headers=headers, json=data)
            response.raise_for_status()

            response_json = response.json()

            summary = response_json["choices"][0]["message"]["content"].strip()
            summaries.append(summary)

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error occurred while communicating with the OpenAI API"
            )

    
    return {
        "summary": " ".join(summaries)
    }


@app.post("/api/publish-medium")
async def publish_summaries(data: schemas.Summary, user: schemas.User = Depends(services.get_user_by_token)):

    MEDIUM_ID = os.getenv("MEDIUM_ID")
    MEDIUM_TOKEN = os.getenv("MEDIUM_TOKEN")

    MEDIUM_URL = f"https://api.medium.com/v1/users/{MEDIUM_ID}/posts"

    content = data.summary

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MEDIUM_TOKEN}",
        "Accept": "application/json",
    }

    data = {
        "title": "title",
        "contentFormat": "markdown",
        "content": content,
        "tags": ["Automation", "Food"],
        "canonicalUrl": "https://medium.com/@taeheechoi",
        "publishStatus": "draft",
    }

    try:
        response = requests.post(MEDIUM_URL, headers=headers, json=data)
        response.raise_for_status()
        return {"message": "Successfully published to Medium"}

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error occurred while communicating with MEDIUM API"
        )
