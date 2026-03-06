from flask import Flask, request, jsonify, Response
import yt_dlp
import requests
import re

app = Flask(__name__)

def validate_url(url):
    if not url:
        return False, "A URL do vídeo é obrigatória."
    yt_regex = r"^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$"
    if not re.match(yt_regex, url):
         return False, "Domínio não autorizado. Use apenas links do YouTube."
    return True, ""

def sanitize_filename(name):
    return re.sub(r'[^\w\s-]', '', name)[:200] or 'video'

@app.route('/api/download', methods=['GET'])
def download():
    url = request.args.get('url')
    itag = request.args.get('itag')

    is_valid, err_msg = validate_url(url)
    if not is_valid:
        return jsonify({'error': err_msg}), 400

    if not itag or not itag.isdigit():
        return jsonify({'error': 'ID de stream (itag) inválido.'}), 400

    ydl_opts = {
        'format': str(itag),
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': ['player_client=ios,tv', 'player_skip=webpage,configs']
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            format_info = ydl.extract_info(url, download=False)
            
        direct_url = format_info.get('url')
        if not direct_url:
            raise Exception("URL de stream direta não encontrada")
            
        clean_title = sanitize_filename(format_info.get('title', 'Video'))
        ext = format_info.get('ext', 'mp4')
        
        has_audio = format_info.get('acodec') != 'none'
        has_video = format_info.get('vcodec') != 'none'
        
        if has_audio and not has_video:
            content_type = 'audio/mpeg' if 'webm' in ext else 'audio/mp4'
            file_extension = 'mp3' if 'webm' in ext else 'm4a'
        else:
            content_type = f'video/{ext}'
            file_extension = ext

        # Criação de um chunked Generator pipe (Proxy do Google > Vercel > User)
        req = requests.get(direct_url, stream=True)
        
        def generate():
            for chunk in req.iter_content(chunk_size=4096):
                yield chunk

        headers = {
            'Content-Disposition': f'attachment; filename="{clean_title}.{file_extension}"',
            'Content-Type': content_type
        }
        
        return Response(generate(), headers=headers)

    except Exception as e:
        return jsonify({'error': 'Erro no stream do youtube', 'details': str(e)}), 500


