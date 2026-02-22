import yt_dlp
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

app = FastAPI()

YDL_OPTS = {
    "format": "best[ext=mp4]/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
}

@app.get("/")
def root():
    return {"status": "Backend running"}

@app.get("/info")
def get_video_info(url: str = Query(...)):
    """
    Returns video metadata + direct download URL
    """
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)

        return JSONResponse({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
            "video_url": info.get("url")
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download")
def download_video(url: str = Query(...)):
    """
    Redirects user directly to TikTok CDN
    This avoids Railway IP block
    """
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get("url")

        if not video_url:
            raise HTTPException(status_code=400, detail="Could not extract video")

        # Redirect user directly to TikTok video file
        return RedirectResponse(video_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
