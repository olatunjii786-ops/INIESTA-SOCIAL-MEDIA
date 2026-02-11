from fastapi import FastAPI, Query
import yt_dlp

app = FastAPI()

@app.get("/iniesta")
def get_video(url: str = Query(..., description="The video URL")):
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # Return the direct download link and title
            return {
                "status": "success",
                "title": info.get('title', 'Video'),
                "download_url": info.get('url')
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
    