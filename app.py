import yt_dlp
from fastapi import FastAPI, HTTPException
import os

app = FastAPI()

def get_ydl_opts():
    return {
        # CRITICAL: This mimics a real browser's hardware signature (TLS)
        'impersonate': 'chrome', 
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'noplaylist': True,
        # Forces IPv4 because Render's IPv6 is often blacklisted
        'source_address': '0.0.0.0', 
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
        },
    }

@app.get("/api/extract")
async def extract_link(url: str):
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            # download=False only grabs the metadata and direct stream URL
            info = ydl.extract_info(url, download=False)
            
            return {
                "success": True,
                "title": info.get('title'),
                "download_url": info.get('url'),
                "thumbnail": info.get('thumbnail'),
                "provider": info.get('extractor')
            }
    except Exception as e:
        # If the site blocks Render's IP, this will catch it
        error_msg = str(e)
        if "403" in error_msg:
            return {"success": False, "error": "Bypass failed. Site is blocking this IP."}
        return {"success": False, "error": error_msg}

if __name__ == "__main__":
    # Render requires binding to the PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
