import yt_dlp
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
import os
import uuid

app = FastAPI()

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.get("/download")
def download_video(url: str = Query(...)):
    try:
        filename = f"{uuid.uuid4()}.mp4"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": filepath,
            "quiet": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="Download failed")

        return FileResponse(
            path=filepath,
            media_type="video/mp4",
            filename="video.mp4"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
