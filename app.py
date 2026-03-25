import os
import re
import time
import yt_dlp
import requests
import traceback
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ================= CONFIG ================= #

BASE_YDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "retries": 3,
    "fragment_retries": 3,
    "socket_timeout": 15,
    "nocheckcertificate": True,
    "http_headers": {
        "User-Agent": "Mozilla/5.0",
    }
}

COOKIES_FILE = "cookies.txt"  # optional
PROXY = None  # e.g. "http://user:pass@host:port"


# ================= HELPERS ================= #

def detect_platform(url):
    patterns = {
        "tiktok": r"(tiktok\.com|douyin\.com)",
        "youtube": r"(youtube\.com|youtu\.be)",
        "instagram": r"instagram\.com",
        "facebook": r"facebook\.com|fb\.watch",
        "twitter": r"twitter\.com|x\.com",
    }
    for name, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return name
    return "unknown"


def get_ydl_opts(use_cookies=False):
    opts = BASE_YDL_OPTS.copy()

    if use_cookies and os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE

    if PROXY:
        opts["proxy"] = PROXY

    return opts


def safe_extract(url, retries=2, use_cookies=False):
    last_error = None

    for _ in range(retries):
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts(use_cookies)) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            last_error = e

    raise last_error


def get_best_url(info, format_id=None):
    formats = info.get("formats", [])

    if format_id:
        for f in formats:
            if f.get("format_id") == format_id:
                return f.get("url")

    # Prefer mp4 with audio
    for f in reversed(formats):
        if f.get("ext") == "mp4" and f.get("acodec") != "none":
            return f.get("url")

    # fallback
    for f in reversed(formats):
        if f.get("url"):
            return f.get("url")

    return info.get("url")


def safe_stream(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Connection": "keep-alive"
    }

    try:
        r = requests.get(url, headers=headers, stream=True, timeout=20)

        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"

        return r.iter_content(chunk_size=8192), None

    except requests.exceptions.RequestException as e:
        return None, str(e)


def clean_filename(name):
    return re.sub(r'[^\w\s-]', '', name)


# ================= CORE ================= #

def extract_info_handler(url):
    try:
        # Try normal
        try:
            info = safe_extract(url)
        except:
            # Retry with cookies
            info = safe_extract(url, use_cookies=True)

        formats = []

        for f in info.get("formats", []):
            if f.get("vcodec") != "none":
                formats.append({
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "resolution": f.get("resolution"),
                    "filesize_mb": round(f.get("filesize", 0) / (1024*1024), 2) if f.get("filesize") else None
                })

        return {
            "success": True,
            "platform": detect_platform(url),
            "title": info.get("title"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "formats": formats
        }

    except Exception as e:
        return {
            "success": False,
            "error": "Extraction failed",
            "details": str(e)
        }


def stream_handler(url, format_id=None, audio_only=False):
    try:
        # Try extraction
        try:
            info = safe_extract(url)
        except:
            info = safe_extract(url, use_cookies=True)

        if audio_only:
            media_url = None
            for f in info.get("formats", []):
                if f.get("acodec") != "none" and f.get("vcodec") == "none":
                    media_url = f.get("url")
                    break
        else:
            media_url = get_best_url(info, format_id)

        if not media_url:
            return None, "No media URL found"

        stream, err = safe_stream(media_url)
        if not stream:
            return None, err

        title = clean_filename(info.get("title", "media"))

        if audio_only:
            filename = f"{title}.mp3"
            content_type = "audio/mpeg"
        else:
            filename = f"{title}.mp4"
            content_type = "video/mp4"

        return (stream, filename, content_type)

    except Exception as e:
        return None, str(e)


# ================= ROUTES ================= #

@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "service": "yt-dlp API"
    })


@app.route("/info", methods=["POST"])
def info():
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"success": False, "error": "URL required"}), 400

    return jsonify(extract_info_handler(data["url"]))


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"success": False, "error": "URL required"}), 400

    result = stream_handler(
        data["url"],
        format_id=data.get("format_id"),
        audio_only=False
    )

    if not result:
        return jsonify({"success": False, "error": "Download failed"}), 500

    stream, filename, content_type = result

    return Response(
        stream_with_context(stream),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        content_type=content_type
    )


@app.route("/download/audio", methods=["POST"])
def download_audio():
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"success": False, "error": "URL required"}), 400

    result = stream_handler(data["url"], audio_only=True)

    if not result:
        return jsonify({"success": False, "error": "Download failed"}), 500

    stream, filename, content_type = result

    return Response(
        stream_with_context(stream),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        content_type=content_type
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": time.time()})


# ================= RUN ================= #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)