from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import os
import uuid

app = FastAPI()

class DownloadRequest(BaseModel):
    url: str
    quality: str = "best"   # default to best

@app.post("/download")
def download_video(req: DownloadRequest):
    filename = f"/tmp/{uuid.uuid4()}.mp4"

    # Build format string
    fmt = "bestvideo+bestaudio/best" if req.quality == "best" else f"best[height<={req.quality.replace('p','')}]"

    ydl_opts = {
        "outtmpl": filename,
        "format": fmt,
        "merge_output_format": "mp4",
        "http_headers": {"User-Agent": "Mozilla/5.0"},
        "noplaylist": True,
        "retries": 5,
        "fragment_retries": 5,
        "sleep_interval": 2,
        "max_sleep_interval": 5,
        "cookiefile": "cookies.txt",   # ← uses your uploaded cookies
        "extractor_args": {"youtube": {"player_client": ["android"]}},  # ← avoids bot check
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([req.url])
        return FileResponse(filename, filename="video.mp4", media_type="video/mp4")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(filename):
            os.remove(filename)