from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import uuid
import logging
import time
from functools import wraps

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# Simple rate limiting
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
            '/download': 'GET with ?url= to download video'
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
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get available formats
            formats = []
            for f in info.get('formats', []):
                if f.get('height') or f.get('format_note'):
                    formats.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'quality': f.get('format_note', str(f.get('height', 'unknown'))),
                        'filesize': f.get('filesize', 0)
                    })
            
            return jsonify({
                'success': True,
                'title': info.get('title', 'Unknown'),
                'uploader': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': formats[:10]
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download')
@rate_limit
def download():
    url = request.args.get('url')
    format_id = request.args.get('format', 'best')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL parameter required'}), 400
    
    # Create unique temp directory
    temp_dir = tempfile.mkdtemp()
    temp_template = os.path.join(temp_dir, '%(title)s_%(id)s.%(ext)s')
    
    ydl_opts = {
        'outtmpl': temp_template,
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'retries': 3,
    }
    
    if format_id and format_id != 'best':
        ydl_opts['format'] = format_id
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info and download
            info = ydl.extract_info(url, download=True)
            
            # Find the downloaded file
            filename = ydl.prepare_filename(info)
            
            # Handle case where file extension might be different
            if not os.path.exists(filename):
                base = filename.rsplit('.', 1)[0]
                possible_extensions = ['.mp4', '.webm', '.mkv']
                for ext in possible_extensions:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break
            
            if not os.path.exists(filename):
                # Try to find any file in temp_dir
                files = os.listdir(temp_dir)
                if files:
                    filename = os.path.join(temp_dir, files[0])
                else:
                    raise Exception("Downloaded file not found")
            
            # Get file size
            file_size = os.path.getsize(filename)
            
            # Read file and delete after sending
            with open(filename, 'rb') as f:
                file_data = f.read()
            
            # Clean up
            try:
                os.unlink(filename)
                os.rmdir(temp_dir)
            except:
                pass
            
            # Determine extension for download name
            ext = filename.split('.')[-1]
            download_name = f"{info.get('title', 'video')}.{ext}"
            
            # Send file
            response = send_file(
                io.BytesIO(file_data),
                as_attachment=True,
                download_name=download_name,
                mimetype='application/octet-stream'
            )
            response.headers['Content-Length'] = file_size
            return response
            
    except Exception as e:
        # Clean up on error
        try:
            os.rmdir(temp_dir)
        except:
            pass
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
