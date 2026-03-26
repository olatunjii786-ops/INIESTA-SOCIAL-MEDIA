from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os, uuid, yt_dlp, shutil
from pathlib import Path

app = FastAPI(title="Universal Social Media Downloader")
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

class DownloadRequest(BaseModel):
    url: str
    quality: str = "best" # e.g. "best", "720p", "480p"

@app.post("/info")
def get_info(req: DownloadRequest):
    ydl_opts = {"quiet": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
        return {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "formats": [f.get("format_note") for f in info.get("formats", []) if f.get("format_note")]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
def download(req: DownloadRequest):
    file_id = str(uuid.uuid4())
    out_path = DOWNLOAD_DIR / f"{file_id}.%(ext)s"

    ydl_opts = {
        "format": req.quality,
        "outtmpl": str(out_path),
        "merge_output_format": "mp4",
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            filename = ydl.prepare_filename(info)
            if not filename.endswith(".mp4"):
                filename = f"{filename}.mp4"
        return FileResponse(filename, filename=os.path.basename(filename))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # clean up old files (keep disk small on free tier)
        shutil.rmtree(DOWNLOAD_DIR, ignore_errors=True)
        DOWNLOAD_DIR.mkdir(exist_ok=True)