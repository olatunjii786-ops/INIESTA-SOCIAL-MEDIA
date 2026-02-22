import yt_dlp
import requests
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/download")
def download_video(url: str = Query(...)):
    # 1. Get the direct URL of the video file without downloading it to server
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # Best quality that includes both video and audio
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Setting download=False only extracts the direct .mp4 link
            info = ydl.extract_info(url, download=False)
            video_direct_url = info.get('url')
            
            if not video_direct_url:
                raise HTTPException(status_code=404, detail="Direct video URL not found")

        # 2. Open a stream to the source (e.g., YouTube/Instagram servers)
        source_response = requests.get(video_direct_url, stream=True, timeout=30)
        
        # 3. Stream chunks of the video back to the Android app
        def stream_generator():
            for chunk in source_response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    yield chunk

        return StreamingResponse(
            stream_generator(),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f'attachment; filename="video.mp4"',
                # This ensures your Android progress bar works!
                "Content-Length": source_response.headers.get("Content-Length", "")
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
