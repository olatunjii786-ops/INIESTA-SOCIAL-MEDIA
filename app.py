import os
import yt_dlp
from fastapi import FastAPI, HTTPException

app = FastAPI()

# Configuration for our cookie files
COOKIE_MAP = {
    "youtube": "yt_cookies.txt",
    "youtu.be": "yt_cookies.txt",
    "tiktok": "tk_cookies.txt"
}

def get_cookie_path(url):
    # Standard loop to check which platform the URL belongs to
    for platform, filename in COOKIE_MAP.items():
        if platform in url.lower():
            # Only return if the file actually exists on your server
            if os.path.exists(filename):
                return filename
    return None

@app.get("/fetch")
def fetch_video(url: str):
    cookie_file = get_cookie_path(url)
    
    # yt-dlp options
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
    }
    
    # If we found a matching cookie file, add it to the options
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info without downloading yet
            info = ydl.extract_info(url, download=False)
            
            return {
                "status": "success",
                "title": info.get("title", "No Title"),
                "thumbnail": info.get("thumbnail"),
                "video_url": info.get("url"), # Direct download link
                "platform": info.get("extractor_key"),
                "duration": info.get("duration")
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Use 0.0.0.0 so you can access it from your phone/other devices
    uvicorn.run(app, host="0.0.0.0", port=8000)
