from flask import Flask, request, Response, jsonify
import yt_dlp
from pytube import YouTube
import requests

app = Flask(__name__)

COOKIES_FILE = "cookies.txt"

@app.route("/")
def home():
    return "Hybrid downloader running"

@app.route("/download")
def download():
    url = request.args.get("url")

    if not url:
        return jsonify({"error": "No URL"}), 400

    # 🔹 FIRST: Try yt-dlp
    try:
        def stream_yt_dlp():
            ydl_opts = {
                "format": "best",
                "cookiefile": COOKIES_FILE,
                "quiet": True,
                "noplaylist": True,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0"
                },
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_url = info["url"]

            r = requests.get(video_url, stream=True)
            for chunk in r.iter_content(8192):
                if chunk:
                    yield chunk

        return Response(
            stream_yt_dlp(),
            mimetype="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename=video.mp4"}
        )

    except Exception as e:
        print("yt-dlp failed:", e)

    # 🔹 SECOND: Fallback to pytube (YouTube only)
    try:
        if "youtube.com" in url or "youtu.be" in url:
            yt = YouTube(url)
            stream = yt.streams.get_highest_resolution()
            video_url = stream.url

            def stream_pytube():
                r = requests.get(video_url, stream=True)
                for chunk in r.iter_content(8192):
                    if chunk:
                        yield chunk

            return Response(
                stream_pytube(),
                mimetype="application/octet-stream",
                headers={"Content-Disposition": "attachment; filename=video.mp4"}
            )

    except Exception as e:
        print("pytube failed:", e)

    return jsonify({"error": "Download failed"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)