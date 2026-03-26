from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import requests

app = FastAPI()

class DownloadRequest(BaseModel):
    url: str
    quality: str = "best"

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/download")
def download_video(req: DownloadRequest):
    # Cobalt expects "max" for best quality
    cobalt_quality = "max" if req.quality == "best" else req.quality.replace("p", "")

    payload = {
        "url": req.url,
        "vQuality": cobalt_quality
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        resp = requests.post("https://co.wuk.sh/api/json",
                             json=payload,
                             headers=headers,
                             timeout=30)

        if resp.status_code != 200:
            raise HTTPException(status_code=502,
                                detail=f"Cobalt returned {resp.status_code}: {resp.text}")

        data = resp.json()

        if data.get("status") != "success":
            raise HTTPException(status_code=400,
                                detail=data.get("text", "Cobalt failed"))

        # Send the phone straight to the file
        return RedirectResponse(data["url"])

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Request to Cobalt failed: {e}")