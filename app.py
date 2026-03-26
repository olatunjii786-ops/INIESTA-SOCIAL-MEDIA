from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import os
import uuid

app = FastAPI()

class DownloadRequest(BaseModel):
    url: str
    quality: str = "best"   # ← use best instead of 720p

@app.post("/download")
def download_video(req: DownloadRequest):
    filename = f"/tmp/{uuid.uuid4()}.mp4"

    # Build format string
    if req.quality == "best":
        fmt = "bestvideo+bestaudio/best"
    else:
        # e.g. "720p" → best[height<=720]
        height = req.quality.replace("p", "")
        fmt = f"best[height<={height}]/best"

    ydl_opts = {
        "outtmpl": filename,
        "format": fmt,
        "merge_output_format": "mp4",
        "http_headers": {"User-Agent": "Mozilla/5.0"},
        "noplaylist": True,
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