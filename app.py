import webview
from pytube import YouTube

video = {
    'url': '',
    'title': '',
    'thumbnail': '',
    'status': '',
}

# Função para capturar a URL e baixar o vídeo
def YtDownload():
    video['url'] = webview.evaluate_js('document.getElementById("floatingInput").value')
    
    if video['url']:
        try:
            youtube = YouTube(video['url'])
            video['title'] = youtube.title
            video['thumbnail'] = youtube.thumbnail_url
            
            # Atualiza a interface com o título do vídeo
            webview.evaluate_js(f'document.getElementById("title").innerText = "Título: {video["title"]}";')
            
            # Baixa o vídeo
            stream = youtube.streams.get_highest_resolution()
            stream.download()
            
            video['status'] = 'Download concluído!'
            webview.evaluate_js(f'document.getElementById("status").innerText = "{video["status"]}";')
        except Exception as e:
            video['status'] = f"Erro: {str(e)}"
            webview.evaluate_js(f'document.getElementById("status").innerText = "{video["status"]}";')
    else:
        video['status'] = "URL inválida. Insira um link do YouTube."
        webview.evaluate_js(f'document.getElementById("status").innerText = "{video["status"]}";')

# Inicia a aplicação
def main():
    webview.create_window('YouTube Downloader', './UI/index.html')
    webview.start()

if __name__ == '__main__':
    main()
