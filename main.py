from fastapi import FastAPI, Query, Response
import yt_dlp

app = FastAPI()

@app.get("/download")
def download_video(url: str = Query(...)):

    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'outtmpl': 'temp_video.mp4',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        with open(filename, "rb") as f:
            data = f.read()

        return Response(content=data, media_type="video/mp4")

    except Exception as e:
        return {"status": "error", "message": str(e)}
