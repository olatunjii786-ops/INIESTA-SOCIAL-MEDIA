import os
import yt_dlp
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({"status": "Iniesta Server Online", "version": "2.0"})

@app.route('/download')
def download():
    video_url = request.args.get('url')
    download_type = request.args.get('type', 'video')

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best' if download_type == 'audio' else 'best',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            # Get the direct URL from the social media provider
            direct_url = info.get('url')
            title = info.get('title', 'video').replace(' ', '_')
            ext = 'mp3' if download_type == 'audio' else info.get('ext', 'mp4')

            # We redirect the phone directly to the source for maximum speed
            return jsonify({
                "success": True,
                "download_url": direct_url,
                "title": f"{title}.{ext}"
            })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
