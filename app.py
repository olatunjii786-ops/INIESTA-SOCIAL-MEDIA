import os
import yt_dlp
from fastapi import FastAPI, HTTPException

app = FastAPI()

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

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        # This is more compatible with different platforms
        'format': 'best', 
        # Crucial: Pretend to be a real Chrome browser
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # YouTube sometimes hides the URL inside 'formats'
            download_url = info.get("url")
            if not download_url and "formats" in info:
                download_url = info["formats"][-1].get("url")

            return {
                "status": "success",
                "title": info.get("title", "Video"),
                "thumbnail": info.get("thumbnail"),
                "download_url": download_url
            }
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def health():
    return {"status": "online"}
