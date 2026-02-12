from fastapi import FastAPI, Query, Response
import yt_dlp
import os

app = FastAPI()

@app.get("/download")
def download_video(url: str = Query(...)):

    ydl_opts = {
        'format': 'best[ext=mp4]',
        'quiet': True,
        'no_warnings': True,
        'outtmpl': 'temp_video.%(ext)s',
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # Read the file and stream to client
        with open(filename, "rb") as f:
            data = f.read()

        # Delete temp file
        os.remove(filename)

        return Response(content=data, media_type="video/mp4")

    except Exception as e:
        return {"status": "error", "message": str(e)}
