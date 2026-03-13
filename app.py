from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import uuid
import threading
import time
import logging
from functools import wraps

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# -------------------------
# Rate limiting
# -------------------------

RATE_LIMIT = 15
TIME_WINDOW = 60
rate_limit_data = {}

def rate_limit(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr
        now = time.time()

        if ip not in rate_limit_data:
            rate_limit_data[ip] = []

        rate_limit_data[ip] = [t for t in rate_limit_data[ip] if now - t < TIME_WINDOW]

        if len(rate_limit_data[ip]) >= RATE_LIMIT:
            return jsonify({
                "success": False,
                "error": "Too many requests. Try again later."
            }), 429

        rate_limit_data[ip].append(now)
        return f(*args, **kwargs)

    return wrapper


# -------------------------
# Root
# -------------------------

@app.route("/")
def home():
    return jsonify({
        "success": True,
        "name": "INIESTA Downloader PRO",
        "supported_sites": "1000+ sites",
        "endpoints": {
            "/info?url=": "Get video info",
            "/download?url=": "Download best video",
            "/download?url=&type=audio": "Download audio"
        }
    })


# -------------------------
# Health check
# -------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# -------------------------
# Info endpoint
# -------------------------

@app.route("/info")
@rate_limit
def info():

    url = request.args.get("url")

    if not url:
        return jsonify({
            "success": False,
            "error": "Missing URL"
        }), 400

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)

        formats = []

        for f in data.get("formats", []):
            formats.append({
                "format_id": f.get("format_id"),
                "ext": f.get("ext"),
                "resolution": f.get("resolution") or f.get("format_note"),
                "filesize": f.get("filesize"),
                "vcodec": f.get("vcodec"),
                "acodec": f.get("acodec")
            })

        return jsonify({
            "success": True,
            "title": data.get("title"),
            "duration": data.get("duration"),
            "uploader": data.get("uploader"),
            "thumbnail": data.get("thumbnail"),
            "formats": formats[:20]
        })

    except Exception as e:
        logging.error(str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# -------------------------
# Download endpoint
# -------------------------

@app.route("/download")
@rate_limit
def download():

    url = request.args.get("url")
    download_type = request.args.get("type", "video")

    if not url:
        return jsonify({
            "success": False,
            "error": "Missing URL"
        }), 400

    temp_dir = tempfile.mkdtemp()
    unique = str(uuid.uuid4())

    output = os.path.join(temp_dir, f"{unique}.%(ext)s")

    ydl_opts = {
        "outtmpl": output,
        "quiet": True,
        "no_warnings": True,
        "retries": 10,
        "fragment_retries": 10,
        "noplaylist": True
    }

    if download_type == "audio":
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    else:
        ydl_opts["format"] = "bestvideo+bestaudio/best"

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        if download_type == "audio":
            file_path = file_path.rsplit(".", 1)[0] + ".mp3"

        if not os.path.exists(file_path):
            files = os.listdir(temp_dir)
            if files:
                file_path = os.path.join(temp_dir, files[0])

        filename = os.path.basename(file_path)

        def cleanup():
            time.sleep(10)
            try:
                os.remove(file_path)
                os.rmdir(temp_dir)
            except:
                pass

        threading.Thread(target=cleanup).start()

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:

        logging.error(str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# -------------------------
# Run server
# -------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
