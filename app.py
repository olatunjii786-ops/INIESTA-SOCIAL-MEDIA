import os
import re
import yt_dlp
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import io
import time
import json
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)

# Configure yt-dlp options
YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'force_generic_extractor': False,
    'noplaylist': True,  # Don't download playlists
}

# Platform detection patterns
PLATFORM_PATTERNS = {
    'tiktok': r'(tiktok\.com|douyin\.com)',
    'youtube': r'(youtube\.com|youtu\.be)',
    'instagram': r'instagram\.com',
    'facebook': r'facebook\.com|fb\.watch',
    'twitter': r'twitter\.com|x\.com',
    'reddit': r'reddit\.com',
    'pinterest': r'pinterest\.com',
    'vimeo': r'vimeo\.com',
    'dailymotion': r'dailymotion\.com',
    'twitch': r'twitch\.tv',
}

def detect_platform(url):
    """Detect social media platform from URL"""
    for platform, pattern in PLATFORM_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return 'unknown'

def get_video_info(url):
    """Extract video information using yt-dlp"""
    ydl_opts = {
        **YDL_OPTS,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract available formats
            formats = []
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none':  # Video formats
                    format_info = {
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'resolution': f.get('resolution', 'N/A'),
                        'format_note': f.get('format_note', ''),
                        'fps': f.get('fps', 'N/A'),
                        'vcodec': f.get('vcodec', 'N/A'),
                    }
                    
                    # Get filesize if available
                    if f.get('filesize'):
                        format_info['filesize'] = f['filesize']
                        format_info['filesize_mb'] = round(f['filesize'] / (1024 * 1024), 2)
                    elif f.get('filesize_approx'):
                        format_info['filesize'] = f['filesize_approx']
                        format_info['filesize_mb'] = round(f['filesize_approx'] / (1024 * 1024), 2)
                    else:
                        format_info['filesize_mb'] = 'Unknown'
                    
                    formats.append(format_info)
            
            # Get best audio format
            audio_format = None
            for f in info.get('formats', []):
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    audio_format = {
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'acodec': f.get('acodec'),
                        'abr': f.get('abr', 'N/A'),
                    }
                    if f.get('filesize'):
                        audio_format['filesize_mb'] = round(f['filesize'] / (1024 * 1024), 2)
                    break
            
            # Prepare response
            result = {
                'success': True,
                'platform': detect_platform(url),
                'title': info.get('title', 'Untitled'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'upload_date': info.get('upload_date'),
                'view_count': info.get('view_count'),
                'like_count': info.get('like_count'),
                'formats': formats,
                'audio_format': audio_format,
                'url': url
            }
            
            return result
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'platform': detect_platform(url)
        }

def stream_video(url, format_id=None):
    """Stream video directly to client without saving to disk"""
    ydl_opts = {
        **YDL_OPTS,
        'format': format_id if format_id else 'best[height<=720]',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first to get video URL
            info = ydl.extract_info(url, download=False)
            
            # Get the actual video URL
            video_url = None
            if format_id:
                for f in info.get('formats', []):
                    if f.get('format_id') == format_id:
                        video_url = f.get('url')
                        break
            else:
                # Get best format
                video_url = info.get('url')
                if not video_url and info.get('formats'):
                    video_url = info[-1].get('url') if info['formats'] else None
            
            if not video_url:
                return None, "Could not get video URL"
            
            # Stream the video from the URL
            import requests
            response = requests.get(video_url, stream=True)
            
            # Get filename
            title = re.sub(r'[^\w\s-]', '', info.get('title', 'video'))
            ext = info.get('ext', 'mp4')
            filename = f"{title}.{ext}"
            
            return response.iter_content(chunk_size=8192), filename
            
    except Exception as e:
        return None, str(e)

def stream_audio(url):
    """Stream audio directly to client without saving"""
    ydl_opts = {
        **YDL_OPTS,
        'format': 'bestaudio/best',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info
            info = ydl.extract_info(url, download=False)
            
            # Get audio URL
            audio_url = None
            for f in info.get('formats', []):
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    audio_url = f.get('url')
                    break
            
            if not audio_url:
                return None, "Could not get audio URL"
            
            # Stream audio
            import requests
            response = requests.get(audio_url, stream=True)
            
            # Get filename
            title = re.sub(r'[^\w\s-]', '', info.get('title', 'audio'))
            filename = f"{title}.mp3"
            
            return response.iter_content(chunk_size=8192), filename
            
    except Exception as e:
        return None, str(e)

@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        'name': 'Social Media Downloader API',
        'version': '1.0.0',
        'supported_platforms': list(PLATFORM_PATTERNS.keys()),
        'endpoints': {
            '/info': 'POST - Get video information (send {"url": "video_url"})',
            '/download': 'POST - Download video (send {"url": "video_url", "format_id": "optional"})',
            '/download/audio': 'POST - Download audio only',
            '/health': 'GET - Health check'
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

@app.route('/info', methods=['POST'])
def info():
    """Get video information without downloading"""
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'success': False, 'error': 'URL is required'}), 400
    
    url = data['url']
    result = get_video_info(url)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@app.route('/download', methods=['POST'])
def download():
    """Download video - streams directly to client"""
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'success': False, 'error': 'URL is required'}), 400
    
    url = data['url']
    format_id = data.get('format_id')
    
    # Get video info first
    info = get_video_info(url)
    if not info['success']:
        return jsonify(info), 400
    
    # Stream video
    stream_generator, filename = stream_video(url, format_id)
    
    if stream_generator is None:
        return jsonify({'success': False, 'error': filename}), 500
    
    # Return streaming response
    return Response(
        stream_with_context(stream_generator),
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'video/mp4'
        }
    )

@app.route('/download/audio', methods=['POST'])
def download_audio():
    """Download audio only - streams directly to client"""
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'success': False, 'error': 'URL is required'}), 400
    
    url = data['url']
    
    # Get video info first
    info = get_video_info(url)
    if not info['success']:
        return jsonify(info), 400
    
    # Stream audio
    stream_generator, filename = stream_audio(url)
    
    if stream_generator is None:
        return jsonify({'success': False, 'error': filename}), 500
    
    # Return streaming response
    return Response(
        stream_with_context(stream_generator),
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'audio/mpeg'
        }
    )

# Alternative: GET endpoint with URL as query parameter (for direct browser usage)
@app.route('/download', methods=['GET'])
def download_get():
    """Download video via GET request (for direct browser links)"""
    url = request.args.get('url')
    format_id = request.args.get('format_id')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL parameter is required'}), 400
    
    # Get video info first
    info = get_video_info(url)
    if not info['success']:
        return jsonify(info), 400
    
    # Stream video
    stream_generator, filename = stream_video(url, format_id)
    
    if stream_generator is None:
        return jsonify({'success': False, 'error': filename}), 500
    
    # Return streaming response
    return Response(
        stream_with_context(stream_generator),
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'video/mp4'
        }
    )

@app.route('/download/audio', methods=['GET'])
def download_audio_get():
    """Download audio via GET request (for direct browser links)"""
    url = request.args.get('url')
    
    if not url:
        return jsonify({'success': False, 'error': 'URL parameter is required'}), 400
    
    # Get video info first
    info = get_video_info(url)
    if not info['success']:
        return jsonify(info), 400
    
    # Stream audio
    stream_generator, filename = stream_audio(url)
    
    if stream_generator is None:
        return jsonify({'success': False, 'error': filename}), 500
    
    # Return streaming response
    return Response(
        stream_with_context(stream_generator),
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'audio/mpeg'
        }
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)