import json
import re
from flask import Flask, request, jsonify, Response
import yt_dlp
import requests

app = Flask(__name__)

def validate_url(url):
    if not url:
        return False, "A URL do vídeo é obrigatória."
    
    # URL nativa via regex leve
    yt_regex = r"^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$"
    if not re.match(yt_regex, url):
         return False, "Domínio não autorizado. Use apenas links do YouTube."
    return True, ""

def sanitize_filename(name):
    return re.sub(r'[^\w\s-]', '', name)[:200] or 'video'

@app.route('/api/info', methods=['POST', 'OPTIONS'])
def info():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json() or {}
    url = data.get('url')

    is_valid, err_msg = validate_url(url)
    if not is_valid:
        return jsonify({'error': err_msg}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(url, download=False)

        clean_title = sanitize_filename(video_info.get('title', 'Video'))

        mp4_streams = []
        webm_streams = []
        mp3_streams = []
        m4a_streams = []

        seen_mp4 = set()
        seen_webm = set()
        seen_mp3 = set()
        seen_m4a = set()

        for f in video_info.get('formats', []):
            has_audio = f.get('acodec') != 'none'
            has_video = f.get('vcodec') != 'none'
            is_progressive = has_audio and has_video
            ext = (f.get('ext') or '').lower()
            itag = int(f.get('format_id', 0))

            if has_video:
                resolution = f"{f.get('height')}p" if f.get('height') else f.get('format_note')
                if not resolution: continue

                if ext == 'mp4' and resolution not in seen_mp4:
                    seen_mp4.add(resolution)
                    mp4_streams.append({
                        'itag': itag, 'quality': resolution, 'type': 'video',
                        'progressive': is_progressive, 'needs_merge': not is_progressive, 'available': True
                    })
                elif ext == 'webm' and resolution not in seen_webm:
                    seen_webm.add(resolution)
                    webm_streams.append({
                        'itag': itag, 'quality': resolution, 'type': 'video',
                        'progressive': is_progressive, 'needs_merge': not is_progressive, 'available': True
                    })
            if has_audio and not has_video:
                abr = f"{int(f.get('abr', 0))}kbps" if f.get('abr') else 'unknown'

                if ext in ['m4a', 'mp4'] and abr not in seen_m4a:
                    seen_m4a.add(abr)
                    m4a_streams.append({
                        'itag': itag, 'quality': abr, 'type': 'audio',
                        'mime': f"audio/{ext}", 'progressive': False, 'needs_merge': False, 'available': True
                    })
                elif ext == 'webm' and abr not in seen_mp3:
                    seen_mp3.add(abr)
                    mp3_streams.append({
                        'itag': itag, 'quality': abr, 'type': 'audio',
                        'mime': "audio/webm", 'progressive': False, 'needs_merge': False, 'available': True
                    })

        def sort_quality(s):
            q = s['quality']
            try:
                return int(''.join(c for c in q if c.isdigit()))
            except:
                return 0

        mp4_streams.sort(key=sort_quality, reverse=True)
        webm_streams.sort(key=sort_quality, reverse=True)
        m4a_streams.sort(key=sort_quality, reverse=True)
        mp3_streams.sort(key=sort_quality, reverse=True)

        return jsonify({
            'title': video_info.get('title'),
            'thumbnail': video_info.get('thumbnail'),
            'author': video_info.get('uploader', 'YouTube'),
            'duration': video_info.get('duration', 0),
            'ffmpeg': False,
            'safe_title': clean_title,
            'formats': {
                'mp4': mp4_streams,
                'webm': webm_streams,
                'mp3': mp3_streams,
                'm4a': m4a_streams
            }
        })
    except Exception as e:
        return jsonify({'error': 'Erro ao se comunicar com YouTube', 'details': str(e)}), 500


