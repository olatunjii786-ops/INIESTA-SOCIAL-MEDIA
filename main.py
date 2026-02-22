import yt_dlp
import requests
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI()

# Default headers to look like a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}

@app.get("/download")
def download_video(url: str = Query(...)):
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'user_agent': HEADERS["User-Agent"],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Extract only the direct video link (no download to server)
            info = ydl.extract_info(url, download=False)
            video_url = info.get('url')
            
            # 2. Use specific headers required by the site (crucial for TikTok)
            site_headers = info.get('http_headers', HEADERS)

        # 3. Stream from the source using the site's required headers
        res = requests.get(video_url, headers=site_headers, stream=True, timeout=30)
        
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail="Source blocked request")

        def stream_generator():
            # Stream in 64KB chunks
            for chunk in res.iter_content(chunk_size=1024 * 64):
                if chunk:
                    yield chunk

        # 4. Return the stream to the Android app
        return StreamingResponse(
            stream_generator(),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f'attachment; filename="video.mp4"',
                "Content-Length": res.headers.get("Content-Length", "")
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
