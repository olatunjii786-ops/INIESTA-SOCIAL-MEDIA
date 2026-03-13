from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import uuid
import threading
import time
import logging
import io
from functools import wraps

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Rate limiting
rate_limit_dict = {}
RATE_LIMIT = 10
TIME_WINDOW = 60

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        current_time = time.time()
        
        if ip in rate_limit_dict:
            rate_limit_dict[ip] = [t for t in rate_limit_dict[ip] 
                                  if current_time - t < TIME_WINDOW]
        else:
            rate_limit_dict[ip] = []
        
        if len(rate_limit_dict[ip]) >= RATE_LIMIT:
            return jsonify({
                'success': False, 
                'error': 'Rate limit exceeded. Try again in a minute.'
            }), 429
        
        rate_limit_dict[ip].append(current_time)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return jsonify({
        'success': True,
        'message': 'INIESTA Downloader API is running',
        'endpoints': {
            '/info': 'GET with ?url= to get video info',
            '/download': 'GET with ?url=&format= to download'
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/info')
@rate_limit
def get_info():
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'URL parameter required'}), 400
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'impersonate': 'chrome-131',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = []
            for f in info.get('formats', []):
                if f.get('height') or f.get('format_note'):
                    formats.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'quality': f.get('format_note', str(f.get('height', 'unknown'))),
                        'filesize': f.get('filesize', 0),
                        'vcodec': f.get('vcodec', 'none'),
                        'acodec': f.get('acodec', 'none')
                    })
            
            return jsonify({
                'success': True,
                'title': info.get('title', 'Unknown'),
                'uploader': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': formats[:15]
            })
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Info error: {error_msg}")
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/download')
@rate_limit
def download():
    url = request.args.get('url')
    format_id = request.args.get('format', 'best')
    download_type = request.args.get('type', 'video')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL parameter required'}), 400
    
    temp_dir = tempfile.mkdtemp()
    
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, '%(title)s_%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'retries': 5,
        'fragment_retries': 5,
        'impersonate': 'chrome-131',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        }
    }
    
    if download_type == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        if format_id and format_id != 'best':
            ydl_opts['format'] = format_id
        else:
            ydl_opts['format'] = 'best[ext=mp4]/best'
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if not info:
                raise Exception("Failed to extract video info")
            
            if download_type == 'audio':
                filename = os.path.join(temp_dir, f"{info.get('title', 'audio')}_{info.get('id', 'unknown')}.mp3")
            else:
                filename = ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    base = filename.rsplit('.', 1)[0]
                    for ext in ['.mp4', '.webm', '.mkv']:
                        if os.path.exists(base + ext):
                            filename = base + ext
                            break
            
            if not os.path.exists(filename):
                files = os.listdir(temp_dir)
                if files:
                    filename = os.path.join(temp_dir, files[0])
                else:
                    raise Exception("Downloaded file not found")
            
            file_size = os.path.getsize(filename)
            
            with open(filename, 'rb') as f:
                file_data = f.read()
            
            @after_this_request
            def cleanup(response):
                def remove_files():
                    time.sleep(5)
                    try:
                        if os.path.exists(filename):
                            os.unlink(filename)
                        os.rmdir(temp_dir)
                    except Exception as e:
                        logging.error(f"Cleanup error: {e}")
                threading.Thread(target=remove_files).start()
                return response
            
            ext = filename.split('.')[-1]
            download_name = f"{info.get('title', 'video').replace('/', '_')}.{ext}"
            
            response = send_file(
                io.BytesIO(file_data),
                as_attachment=True,
                download_name=download_name,
                mimetype='application/octet-stream'
            )
            response.headers['Content-Length'] = str(file_size)
            return response
            
    except Exception as e:
        try:
            os.rmdir(temp_dir)
        except:
            pass
        
        error_msg = str(e)
        logging.error(f"Download error: {error_msg}")
        
        if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
            return jsonify({
                'success': False, 
                'error': 'Platform is blocking automated downloads. Try again later.'
            }), 503
        else:
            return jsonify({'success': False, 'error': error_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
