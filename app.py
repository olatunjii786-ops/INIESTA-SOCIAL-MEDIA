from flask import Flask, request, Response, jsonify
import yt_dlp
import os

app = Flask(__name__)

COOKIES_FILE = "cookies.txt"

@app.route("/")
def home():
    return "Server is running"

@app.route("/download")
def download():
    url = request.args.get("url")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    def generate():
        ydl_opts = {
            "format": "best",
            "cookiefile": COOKIES_FILE,
            "quiet": True,
            "noplaylist": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                direct_url = info["url"]

            import requests
            with requests.get(direct_url, stream=True) as r:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

        except Exception as e:
            yield f"ERROR: {str(e)}".encode()

    return Response(
        generate(),
        mimetype="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename=video.mp4"
        },
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)