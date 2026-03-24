from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)

@app.route('/download')
def get_link():
    url = request.args.get('url')
    if not url:
        return jsonify({"success": False, "error": "No URL"}), 400

    # These options ensure the server NEVER saves the video
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True, # CRITICAL: Stop Render from downloading
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract the actual direct video link and title
            direct_link = info.get('url')
            title = info.get('title', 'video')
            
            return jsonify({
                "success": True,
                "download_url": direct_link,
                "title": title
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
