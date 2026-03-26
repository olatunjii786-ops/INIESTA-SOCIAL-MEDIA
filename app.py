from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel
import requests

app = FastAPI()

class DownloadRequest(BaseModel):
    url: str
    quality: str = "best"   # "best" or "720", "480", etc.

@app.post("/download")
def download_video(req: DownloadRequest):
    # Map your "best" to Cobalt's "max"
    cobalt_quality = "max" if req.quality == "best" else req.quality.replace("p", "")

    payload = {
        "url": req.url,
        "vQuality": cobalt_quality,
        "aFormat": "mp3",
        "isAudioOnly": False
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        resp = requests.post("https://co.wuk.sh/api/json", json=payload, headers=headers, timeout=30)
        data = resp.json()

        if data.get("status") != "success":
            raise HTTPException(status_code=400, detail=data.get("text", "Cobalt error"))

        # Cobalt returns a direct download URL
        video_url = data["url"]
        # Redirect the client straight to the file (fastest, no server bandwidth)
        return RedirectResponse(video_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))