from flask import Flask, request, Response, jsonify
import yt_dlp
import requests

app = Flask(__name__)


def get_direct_url(video_url):
    ydl_opts = {
        "quiet": True,
        "format": "best",
        "noplaylist": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        # Try direct URL
        if "url" in info:
            return info["url"]

        # fallback
        formats = info.get("formats", [])
        for f in reversed(formats):
            if f.get("url"):
                return f["url"]

        return None

    except Exception as e:
        return None


@app.route("/")
def home():
    return "Simple Downloader API"


@app.route("/download", methods=["GET"])
def download():
    video_url = request.args.get("url")

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    media_url = get_direct_url(video_url)

    if not media_url:
        return jsonify({"error": "Failed to extract video"}), 500

    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(media_url, stream=True, headers=headers, timeout=20)

        return Response(
            r.iter_content(chunk_size=8192),
            content_type="video/mp4",
            headers={
                "Content-Disposition": "attachment; filename=video.mp4"
            }
        )

    except Exception:
        return jsonify({"error": "Streaming failed"}), 500


if __name__ == "__main__":
    app.run()