from flask import Flask, request, Response, jsonify
import requests
import yt_dlp

app = Flask(__name__)

def extract_url(video_url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info["url"]
    except:
        return None


@app.route("/download", methods=["GET"])
def download():
    video_url = request.args.get("url")

    if not video_url:
        return jsonify({"error": "Missing URL"}), 400

    media_url = extract_url(video_url)

    if not media_url:
        return jsonify({"error": "Extraction failed"}), 500

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": video_url
    }

    try:
        r = requests.get(media_url, stream=True, headers=headers, timeout=20)

        if r.status_code != 200:
            return jsonify({"error": "Blocked by source"}), 403

        content_type = r.headers.get("Content-Type", "")

        if "text/html" in content_type:
            return jsonify({"error": "Invalid response (HTML blocked)"}), 500

        return Response(
            r.iter_content(chunk_size=8192),
            content_type=content_type,
            headers={
                "Content-Disposition": "attachment; filename=video.mp4"
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)