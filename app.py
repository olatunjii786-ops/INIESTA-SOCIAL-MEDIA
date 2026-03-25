import yt_dlp
from fastapi import FastAPI, HTTPException
import os

app = FastAPI()

def get_ydl_opts():
    return {
        'impersonate': 'chrome',
        'quiet': True,
        'no_warnings': True,
        # 'best' can sometimes return a webpage. 
        # This ensures we look for a direct media stream.
        'format': 'best[ext=mp4]/best', 
        'noplaylist': True,
        'source_address': '0.0.0.0',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }

@app.get("/api/extract")
async def extract(url: str):
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            # 1. Extract raw info
            info = ydl.extract_info(url, download=False)
            
            # 2. Sanitize info (Official yt-dlp way to clean data)
            clean_info = ydl.sanitize_info(info)
            
            # 3. Carefully pick the download URL
            # Some sites put it in 'url', some in 'formats'
            download_url = clean_info.get('url')
            if not download_url and clean_info.get('formats'):
                # Pick the last format (usually the best quality)
                download_url = clean_info['formats'][-1].get('url')

            if not download_url:
                return {"success": False, "error": "No direct link found for this video."}

            return {
                "success": True,
                "title": clean_info.get('title', 'video'),
                "download_url": download_url,
                "thumbnail": clean_info.get('thumbnail')
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
