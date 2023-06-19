import json
import os
import textwrap
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from googleapiclient import discovery

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from .model import Token,  User, Transcript
from .auth import authenticate_user, users, create_access_token, get_current_active_user

load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))

app = FastAPI()


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(
        users, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/youtube-videos")
async def get_youtube_videos(search_params: dict, current_user: User = Depends(get_current_active_user)):
    youtube_api_key = os.getenv('YOUTUBE_API_KEY')

    default_search_params = {
        'q': '',
        'type': 'video',
        'part': 'id,snippet',
        'order': 'viewCount',
        'videoCaption': 'closedCaption',
        'videoDuration': 'medium',
        'maxResults': 10,
        'publishedAfter': (datetime.now() - timedelta(days=7)).isoformat() + 'Z'
    }

    q = search_params.get('q')
    if not q:
        raise HTTPException(
            status_code=400, detail="Parameter 'q' is required and must not be blank.")

    default_search_params.update(search_params)

    youtube = discovery.build('youtube', 'v3', developerKey=youtube_api_key)

    try:
        videos = youtube.search().list(**default_search_params).execute()
        video_ids = [video['id']['videoId'] for video in videos['items']]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve YouTube videos")

    return {
        "video_ids": video_ids
    }


@app.post("/transcript/{video_id}")
async def get_video_transcript(video_id: str, current_user: User = Depends(get_current_active_user)):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id)
        formatter = TextFormatter()
        formatted_transcript = formatter.format_transcript(transcript)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve video transcript")

    return {
        "video_id": video_id,
        "transcript": formatted_transcript
    }


@app.post("/summarize-medium")
async def generate_summaries(transcript: Transcript, current_user: User = Depends(get_current_active_user)):
    openai_api_key = os.getenv('OPENAI_API_KEY')

    transcript_text = transcript.transcript.strip()

    if not transcript_text:
        raise HTTPException(
            status_code=400, detail="Transcript cannot be blank.")

    chunk_size = 1200 if len(transcript_text) >= 2500 else 2000

    chunks = textwrap.wrap(transcript_text, chunk_size)

    summaries = []

    for chunk in chunks:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_api_key}"
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

        response = requests.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        response_json = json.loads(response.text)

        if "error" in response_json:
            print(f"API error: {response_json['error']}")
        else:
            summary = response_json['choices'][0]['message']['content'].strip()
            summaries.append(summary)

    return {
        "summary": " ".join(summaries)
    }
