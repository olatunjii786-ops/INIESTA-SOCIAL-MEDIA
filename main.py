import yt_dlp
import requests
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/download")
def download_video(url: str = Query(...)):
    # 1. Get the direct URL of the video file
    ydl_opts = {
        'format': 'best[ext=mp4]/best', 
        'quiet': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False) # Don't download to server!
            video_direct_url = info.get('url')
            
            if not video_direct_url:
                raise HTTPException(status_code=404, detail="Could not extract video URL")

        # 2. Open a streaming connection to the source
        # We use stream=True so we don't load the whole file into RAM
        source_response = requests.get(video_direct_url, stream=True, timeout=60)

        # 3. Forward the stream to the Android app
        def iter_content():
            for chunk in source_response.iter_content(chunk_size=1024 * 64):
                yield chunk

        return StreamingResponse(
            iter_content(),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f'attachment; filename="video.mp4"',
                "Content-Length": source_response.headers.get("Content-Length", "")
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
