from flask import Flask, request, jsonify, send_file, after_this_request
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
CORS(app)  # Allow your app to call this API
logging.basicConfig(level=logging.INFO)

# Simple rate limiting (3 requests per minute per IP)
rate_limit_dict = {}
RATE_LIMIT = 3
TIME_WINDOW = 60  # seconds

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        current_time = time.time()
        
        # Clean old entries
        if ip in rate_limit_dict:
            rate_limit_dict[ip] = [t for t in rate_limit_dict[ip] 
                                  if current_time - t < TIME_WINDOW]
        else:
            rate_limit_dict[ip] = []
        
        # Check limit
        if len(rate_limit_dict[ip]) >= RATE_LIMIT:
            return jsonify({
                'success': False, 
                'error': 'Rate limit exceeded. Try again later.'
            }), 429
        
        rate_limit_dict[ip].append(current_time)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'message': 'Social Media Downloader API',
        'endpoints': {
            '/info': 'GET with ?url= to get video info',
            '/download': 'GET with ?url=&format= to download'
        }
    })

@app.route('/info')
@rate_limit
def get_info():
    """Get video info without downloading"""
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'URL parameter required'}), 400
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'success': True,
                'title': info.get('title', 'Unknown'),
                'uploader': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': [
                    {
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'quality': f.get('format_note', 'unknown'),
                        'filesize': f.get('filesize', 0)
                    }
                    for f in info.get('formats', [])
                    if f.get('vcodec') != 'none'  # Only video formats
                ][:10]  # Limit to 10 formats to keep response small
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download')
@rate_limit
def download():
    """Download and stream video directly to client"""
    url = request.args.get('url')
    format_type = request.args.get('format', 'best')
    download_type = request.args.get('type', 'video')  # video, audio, thumbnail
    
    if not url:
        return jsonify({'success': False, 'error': 'URL parameter required'}), 400
    
    # Create unique temp file in /tmp (RAM-based on most Linux systems)
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, f'download_{uuid.uuid4()}.%(ext)s')
    
    # Base yt-dlp options
    ydl_opts = {
        'outtmpl': temp_file,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'retries': 3,
    }
    
    # Configure based on download type
    if download_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    elif download_type == 'thumbnail':
        ydl_opts.update({
            'writethumbnail': True,
            'postprocessors': [{
                'key': 'EmbedThumbnail',
            }],
        })
    else:  # video
        ydl_opts.update({
            'format': format_type,
            'merge_output_format': 'mp4',
        })
    
    try:
        # Download the file
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Find the actual downloaded file
            if download_type == 'audio':
                filename = os.path.join(temp_dir, f"{info['title']} [{info['id']}].mp3")
            else:
                # yt-dlp might have changed the filename
                base = ydl.prepare_filename(info)
                if download_type == 'video' and not base.endswith('.mp4'):
                    filename = base.rsplit('.', 1)[0] + '.mp4'
                else:
                    filename = base
            
            # Check if file exists (handle different naming)
            if not os.path.exists(filename):
                # Try to find any file in temp_dir
                files = os.listdir(temp_dir)
                if files:
                    filename = os.path.join(temp_dir, files[0])
                else:
                    raise Exception("Downloaded file not found")
            
            # Schedule file cleanup after sending
            @after_this_request
            def cleanup(response):
                def remove_file():
                    try:
                        os.unlink(filename)
                        os.rmdir(temp_dir)
                        logging.info(f"Cleaned up {filename}")
                    except Exception as e:
                        logging.error(f"Cleanup error: {e}")
                threading.Timer(5.0, remove_file).start()  # Delete after 5 seconds
                return response
            
            # Send file to client
            return send_file(
                filename,
                as_attachment=True,
                download_name=f"{info['title']}.{filename.split('.')[-1]}",
                mimetype='application/octet-stream'
            )
            
    except Exception as e:
        # Clean up on error
        try:
            os.rmdir(temp_dir)
        except:
            pass
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
