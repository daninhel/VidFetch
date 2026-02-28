import os
import re
import shutil
import subprocess
import tempfile
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse, quote

import requests as http_requests
from flask import Flask, request, jsonify, render_template, send_file, Response, after_this_request, make_response, stream_with_context
from pytubefix import YouTube
from pytubefix.cli import on_progress
from pytubefix.exceptions import (
    VideoUnavailable,
    RegexMatchError,
    AgeRestrictedError,
    VideoPrivate,
    MembersOnly,
    RecordingUnavailable,
    LiveStreamError,
)

# ── Logging ───────────────────────────────────────────────────────────────────

# No Vercel, o sistema de arquivos é read-only, com exceção da pasta /tmp
if os.environ.get("VERCEL") == "1":
    LOG_DIR = os.path.join("/tmp", "logs")
else:
    LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            os.path.join(LOG_DIR, "app.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────

app = Flask(__name__)

# ── Security headers ──────────────────────────────────────────────────────────

@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"]  = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["X-XSS-Protection"]        = "1; mode=block"
    response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]      = "geolocation=(), camera=(), microphone=()"
    # CSP: only allow our own assets + Google Fonts + YouTube thumbnails + Vercel Analytics + Vercel Speed Insights
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://va.vercel-scripts.com https://*.vercel-scripts.com; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' https://i.ytimg.com https://*.ytimg.com data:; "
        "connect-src 'self' https://va.vercel-analytics.com https://*.vercel-analytics.com https://vitals.vercel-insights.com; "
        "frame-ancestors 'none';"
    )
    return response

# ── Helpers ───────────────────────────────────────────────────────────────────

# Allowed YouTube hostname patterns (SSRF prevention)
_YT_HOSTNAMES = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}
_PROXY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",          # sem compressão → chunked streaming direto
    "Cache-Control":   "no-cache",
    "Range":           "bytes=0-",          # sinaliza ao CDN que é um download
}


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name[:200]  # limita tamanho do nome


def has_ffmpeg() -> bool:
    """Verifica ffmpeg no PATH do processo e também no PATH do sistema (Windows)."""
    if shutil.which("ffmpeg"):
        return True
    # O servidor pode ter sido iniciado antes do ffmpeg ser instalado;
    # lê o PATH do sistema operacional diretamente (Windows).
    try:
        import winreg
        paths: list[str] = []
        for hive, sub in [
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            (winreg.HKEY_CURRENT_USER,  r"Environment"),
        ]:
            try:
                with winreg.OpenKey(hive, sub) as key:
                    val, _ = winreg.QueryValueEx(key, "PATH")
                    paths.extend(val.split(";"))
            except FileNotFoundError:
                pass
        for p in paths:
            candidate = os.path.join(p, "ffmpeg.exe")
            if os.path.isfile(candidate):
                log.info("FFmpeg encontrado no PATH do sistema: %s", candidate)
                return True
    except Exception:
        pass
    return False


def validate_youtube_url(url: str) -> str | None:
    """
    Valida e normaliza a URL do YouTube.
    Retorna mensagem de erro se inválida, None se OK.
    """
    url = url.strip()
    if not url:
        return "URL não informada. Cole o link do vídeo e tente novamente."
    if len(url) > 2048:
        return "URL muito longa."
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
    except Exception:
        return "URL malformada."
    if parsed.scheme not in ("https", "http"):
        return "Apenas URLs HTTP/HTTPS são aceitas."
    if parsed.hostname not in _YT_HOSTNAMES:
        return (
            "URL não parece ser do YouTube. Cole um link como "
            "https://www.youtube.com/watch?v=... ou https://youtu.be/..."
        )
    return None


def build_yt(url: str) -> YouTube:
    # Fallback robusto para Bot Detection severa em Nuvem (AWS/Vercel)
    clients_to_try = [
        "ANDROID_VR",  # Menos bloqueios recentes para leitura
        "ANDROID",     # Tradicional mobile guest
        "IOS",         # Apple guest
        "MWEB",        # Mobile Web
        "WEB"          # Web clássico
    ]
    last_exc = None
    for c in clients_to_try:
        try:
            yt = YouTube(url, on_progress_callback=on_progress, client=c)
            _ = yt.title  # Força o fetch real para validar se não estamos bloqueados
            return yt
        except Exception as e:
            log.warning("Falha ao buscar com client %s (%s)", c, e)
            last_exc = e
            
    # Se todos falharem (raro se houver VPs saudáveis, comum em soft ban pesado de IP nulo) 
    # lança a última exceção para ser rastreada no log
    raise last_exc


def sort_key(item: dict) -> int:
    q = item.get("quality", "")
    if q and q.endswith("p"):
        try:
            return -int(q[:-1])
        except ValueError:
            pass
    if q and q.endswith("kbps"):
        try:
            return -int(q[:-4])
        except ValueError:
            pass
    return 0


def classify_yt_error(exc: Exception) -> tuple[str, int]:
    """Mensagens amigáveis em PT-BR por tipo de erro."""
    if isinstance(exc, AgeRestrictedError):
        return (
            "Este vídeo é restrito por idade e exige login no YouTube. "
            "Não é possível baixá-lo aqui.",
            403,
        )
    if isinstance(exc, VideoPrivate):
        return "Este vídeo é privado. Apenas o dono pode acessá-lo.", 403
    if isinstance(exc, MembersOnly):
        return "Este vídeo é exclusivo para membros do canal.", 403
    if isinstance(exc, RecordingUnavailable):
        return "A gravação deste evento ao vivo não está disponível.", 404
    if isinstance(exc, LiveStreamError):
        return "Não é possível baixar transmissões ao vivo em andamento.", 400
    if isinstance(exc, VideoUnavailable):
        return (
            "Vídeo indisponível. Ele pode ter sido removido, "
            "tornado privado ou não existe nesta URL.",
            404,
        )
    if isinstance(exc, RegexMatchError):
        return (
            "URL inválida ou não reconhecida pelo YouTube. "
            "Certifique-se de usar um link público e válido.",
            400,
        )
    msg = str(exc).lower()
    if "http error 403" in msg:
        return (
            "O YouTube bloqueou esta requisição (HTTP 403). "
            "Aguarde alguns segundos e tente novamente, ou atualize o pytubefix.",
            503,
        )
    if "http error 404" in msg or "not found" in msg:
        return "Vídeo não encontrado. Verifique o link e tente novamente.", 404
    if any(k in msg for k in ("urllib", "connection", "timeout", "network")):
        return "Erro de conexão com o YouTube. Verifique sua internet e tente novamente.", 503
    return f"Erro inesperado ao processar o vídeo: {exc}", 500


# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    log.info("GET /")
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def video_info():
    data = request.get_json(silent=True) or {}
    url  = (data.get("url") or "").strip()

    err = validate_youtube_url(url)
    if err:
        return jsonify({"error": err}), 400

    log.info("POST /api/info — url=%s", url)

    try:
        yt      = build_yt(url)
        streams = yt.streams
        ffmpeg  = has_ffmpeg()
        log.info("ffmpeg=%s | título='%s'", ffmpeg, yt.title)

        mp4_streams, webm_streams, mp3_streams, m4a_streams = [], [], [], []
        seen_mp4, seen_webm, seen_mp3, seen_m4a = set(), set(), set(), set()

        for s in streams.filter(file_extension="mp4"):
            if s.resolution:
                res = s.resolution
                if res not in seen_mp4:
                    seen_mp4.add(res)
                    needs_merge = not s.is_progressive
                    mp4_streams.append({
                        "itag": s.itag, "quality": res, "type": "video",
                        "progressive": s.is_progressive,
                        "needs_merge": needs_merge,
                        "available": not needs_merge or ffmpeg,
                    })

        for s in streams.filter(file_extension="webm"):
            if s.resolution:
                res = s.resolution
                if res not in seen_webm:
                    seen_webm.add(res)
                    needs_merge = not s.is_progressive
                    webm_streams.append({
                        "itag": s.itag, "quality": res, "type": "video",
                        "progressive": s.is_progressive,
                        "needs_merge": needs_merge,
                        "available": not needs_merge or ffmpeg,
                    })

        for s in streams.filter(only_audio=True):
            abr = s.abr or "?"
            key = f"mp3_{abr}"
            if key not in seen_mp3:
                seen_mp3.add(key)
                mp3_streams.append({
                    "itag": s.itag, "quality": abr, "type": "audio",
                    "mime": s.mime_type, "progressive": False,
                    "needs_merge": False, "available": True,
                })

        for s in streams.filter(only_audio=True, file_extension="mp4"):
            abr = s.abr or "?"
            key = f"m4a_{abr}"
            if key not in seen_m4a:
                seen_m4a.add(key)
                m4a_streams.append({
                    "itag": s.itag, "quality": abr, "type": "audio",
                    "mime": s.mime_type, "progressive": False,
                    "needs_merge": False, "available": True,
                })

        mp4_streams.sort(key=sort_key)
        webm_streams.sort(key=sort_key)
        mp3_streams.sort(key=sort_key)
        m4a_streams.sort(key=sort_key)

        log.info("mp4=%d webm=%d mp3=%d m4a=%d", len(mp4_streams), len(webm_streams), len(mp3_streams), len(m4a_streams))

        return jsonify({
            "title": yt.title, "thumbnail": yt.thumbnail_url,
            "author": yt.author, "duration": yt.length, "ffmpeg": ffmpeg,
            "safe_title": sanitize_filename(yt.title or "video"),
            "formats": {
                "mp4": mp4_streams, "webm": webm_streams,
                "mp3": mp3_streams, "m4a": m4a_streams,
            },
        })

    except Exception as exc:
        msg, status = classify_yt_error(exc)
        log.warning("Erro /api/info (%s): %s", type(exc).__name__, msg)
        return jsonify({"error": msg}), status


@app.route("/api/download")
def download():
    url  = (request.args.get("url")    or "").strip()
    itag = (request.args.get("itag")   or "").strip()
    fmt  = (request.args.get("format") or "mp4").strip().lower()

    # Validação de entrada
    err = validate_youtube_url(url)
    if err:
        return jsonify({"error": err}), 400
    if not itag or not itag.isdigit():
        return jsonify({"error": "ID de stream inválido."}), 400
    itag_int = int(itag)
    if not (0 < itag_int < 1000):
        return jsonify({"error": "ID de stream fora do intervalo permitido."}), 400
    if fmt not in ("mp4", "webm", "mp3", "m4a"):
        return jsonify({"error": "Formato inválido. Use mp4, webm, mp3 ou m4a."}), 400

    log.info("GET /api/download — format=%s itag=%s url=%s", fmt, itag, url)

    try:
        yt     = build_yt(url)
        stream = yt.streams.get_by_itag(itag_int)

        if not stream:
            log.warning("Stream não encontrada — itag=%s", itag)
            return jsonify({
                "error": "Stream não encontrada. Busque o vídeo novamente e escolha outra qualidade."
            }), 404

        safe_title = sanitize_filename(yt.title or "video")

        # ── Streaming proxy sem disco (funciona no Vercel) ────────────────────
        if stream.is_progressive or stream.type == "audio":
            ext_map = {"mp3": "mp3", "m4a": "m4a", "webm": "webm"}
            ext = ext_map.get(fmt) or ("webm" if "webm" in stream.mime_type else "mp4")
            download_name = f"{safe_title}.{ext}"
            stream_url    = stream.url

            # Encaminha Range do cliente para suporte a retomada de download
            proxy_headers = dict(_PROXY_HEADERS)
            client_range  = request.headers.get("Range")
            if client_range:
                proxy_headers["Range"] = client_range

            log.info("Proxy streaming → '%s'", download_name)

            def generate():
                try:
                    with http_requests.get(
                        stream_url, stream=True,
                        timeout=(10, 120),  # (connect, read)
                        headers=proxy_headers,
                        allow_redirects=True,
                    ) as r:
                        r.raise_for_status()
                        for chunk in r.iter_content(chunk_size=65536):
                            if chunk:
                                yield chunk
                except http_requests.RequestException as proxy_err:
                    log.error("Proxy error: %s", proxy_err)
                    # Generator já começou — n��o dá para mudar status code, mas interrompe o stream

            mime_map = {"mp3": "audio/mpeg", "m4a": "audio/mp4", "webm": "video/webm", "mp4": "video/mp4"}
            content_type = mime_map.get(ext, "application/octet-stream")

            # RFC 5987: nome em UTF-8 para suporte a acentos/espaços
            encoded_name = quote(download_name, safe="")
            content_disp = (
                f'attachment; '
                f'filename="{download_name.encode("ascii", "replace").decode()}"; '
                f"filename*=UTF-8''{encoded_name}"
            )

            # usa make_response + stream_with_context para garantir que
            # os headers sejam enviados corretamente na resposta de streaming
            resp = make_response(Response(
                stream_with_context(generate()),
                status=200,
                content_type=content_type,
            ))
            resp.headers["Content-Disposition"] = content_disp
            resp.headers["X-Accel-Buffering"]   = "no"
            resp.headers["Cache-Control"]        = "no-store"
            log.info("Content-Disposition enviado: %s", content_disp)
            return resp

        # ── Stream adaptativa (video-only) → merge FFmpeg ─────────────────────
        if not has_ffmpeg():
            log.warning("Merge solicitado sem FFmpeg — itag=%s", itag)
            return jsonify({
                "error": (
                    "Esta qualidade requer FFmpeg para unir vídeo e áudio. "
                    "Instale o FFmpeg (https://ffmpeg.org) e reinicie o servidor. "
                    "Alternativamente, escolha uma qualidade menor que inclua áudio (marcada com V+A)."
                )
            }), 400

        log.info("Merge com FFmpeg — itag=%s", itag)
        tmp_dir = tempfile.mkdtemp()
        try:
            v_ext  = stream.mime_type.split("/")[-1]
            v_path = stream.download(output_path=tmp_dir, filename=f"video.{v_ext}")

            audio = (
                yt.streams.filter(only_audio=True, file_extension="mp4").order_by("abr").last()
                or yt.streams.filter(only_audio=True).order_by("abr").last()
            )
            if not audio:
                return jsonify({"error": "Nenhuma stream de áudio disponível para mesclar."}), 500

            a_path  = audio.download(output_path=tmp_dir, filename="audio.mp4")
            out_ext = "webm" if fmt == "webm" else "mp4"
            merged  = os.path.join(tmp_dir, f"{safe_title}.{out_ext}")

            result = subprocess.run(
                ["ffmpeg", "-y", "-i", v_path, "-i", a_path, "-c:v", "copy", "-c:a", "aac", merged],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                log.error("FFmpeg falhou:\n%s", result.stderr[-500:])
                return jsonify({"error": "Falha ao mesclar vídeo e áudio. Tente uma qualidade menor."}), 500

            @after_this_request
            def cleanup(response):
                try:
                    for f in os.listdir(tmp_dir):
                        os.remove(os.path.join(tmp_dir, f))
                    os.rmdir(tmp_dir)
                except Exception:
                    pass
                return response

            log.info("Merge concluído → '%s.%s'", safe_title, out_ext)
            return send_file(merged, as_attachment=True, download_name=f"{safe_title}.{out_ext}")

        except Exception:
            # Limpeza garantida
            try:
                for f in os.listdir(tmp_dir):
                    os.remove(os.path.join(tmp_dir, f))
                os.rmdir(tmp_dir)
            except Exception:
                pass
            raise

    except Exception as exc:
        msg, status = classify_yt_error(exc)
        log.warning("Erro /api/download (%s): %s", type(exc).__name__, msg)
        return jsonify({"error": msg}), status


# ── Entrada ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("Servidor iniciado | FFmpeg: %s", has_ffmpeg())
    log.info("=" * 60)
    app.run(debug=True)
