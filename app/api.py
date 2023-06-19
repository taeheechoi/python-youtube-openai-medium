import json
import os
import textwrap
from datetime import datetime, timedelta


import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from googleapiclient import discovery
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

load_dotenv()

app = FastAPI()


@app.post("/youtube-videos")
async def get_youtube_videos(search_params: dict):
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
async def get_video_transcript(video_id: str):
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


class Transcript(BaseModel):
    transcript: str


@app.post("/summarize-medium")
async def generate_summaries(transcript: Transcript):
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
