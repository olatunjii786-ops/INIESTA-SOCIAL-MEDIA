import os
import yt_dlp
from fastapi import FastAPI, HTTPException

app = FastAPI()

# Map the domains to your secret cookie files
# Make sure these filenames match exactly what you set in Render Secret Files
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
        # FIX: 'best[ext=mp4]' forces yt-dlp to find a single-link MP4 
        # or merge them into one playable stream URL.
        'format': 'best[ext=mp4]/best',
        'merge_output_format': 'mp4',
    }

    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # We use download=False to get the metadata and the direct URL
            info = ydl.extract_info(url, download=False)
            
            # For YouTube specifically, if 'url' is missing in the root, 
            # we grab it from the requested formats.
            download_url = info.get("url")
            if not download_url and "formats" in info:
                # Fallback to the last (usually best) format entry if needed
                download_url = info["formats"][-1].get("url")

            return {
                "status": "success",
                "title": info.get("title", "Universal Video"),
                "thumbnail": info.get("thumbnail"),
                "download_url": download_url,
                "platform": info.get("extractor_key"),
                "duration": info.get("duration")
            }
    except Exception as e:
        # This will help you see the exact error in Render logs
        print(f"Error fetching {url}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def health_check():
    return {"message": "Universal Downloader Backend is running!"}
