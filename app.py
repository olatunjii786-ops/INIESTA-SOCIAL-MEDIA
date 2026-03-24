import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

@app.route('/download')
def get_link():
    url = request.args.get('url')
    if not url:
        return jsonify({"success": False, "error": "No URL"}), 400

    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        # TRICK THE BOT DETECTOR:
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        'nocheckcertificate': True,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "success": True,
                "download_url": info.get('url'),
                "title": info.get('title', 'video') + "." + info.get('ext', 'mp4')
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
