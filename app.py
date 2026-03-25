import os
import yt_dlp
from fastapi import FastAPI, HTTPException

app = FastAPI()

# Map the domains to your secret cookie files
COOKIE_MAP = {
    "youtube.com": "yt_cookies.txt",
    "youtu.be": "yt_cookies.txt",
    "tiktok.com": "tk_cookies.txt"
}

def get_cookie_file(url):
    url_lower = url.lower()
    for domain in COOKIE_MAP:
        if domain in url_lower:
            filename = COOKIE_MAP[domain]
            if os.path.exists(filename):
                return filename
    return None

@app.get("/fetch")
def fetch_video(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    cookie_path = get_cookie_file(url)
    
    # yt-dlp Configuration
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        # 'best' ensures we get a single file if possible, or merged high-quality
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
    }

    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # We use download=False because we just want the direct link for the Android app
            info = ydl.extract_info(url, download=False)
            
            return {
                "status": "success",
                "title": info.get("title", "Universal Video"),
                "thumbnail": info.get("thumbnail"),
                "download_url": info.get("url"),
                "platform": info.get("extractor_key"),
                "duration": info.get("duration")
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def health_check():
    return {"message": "Universal Downloader Backend is running!"}
