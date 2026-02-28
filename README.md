# PyTube Downloader

> App web simples para baixar vídeos do YouTube em MP4, WebM, MP3 e M4A.

## Stack

| Camada    | Tecnologia                        |
|-----------|-----------------------------------|
| Backend   | Python 3.11+ · Flask · pytubefix  |
| Frontend  | HTML · CSS · JavaScript (vanilla) |
| Merge A/V | FFmpeg (opcional, para >720p)      |

## Estrutura

```
Pytube/
├── app.py                  # Servidor Flask
├── requirements.txt        # Dependências Python
├── logs/
│   └── app.log             # Log rotativo (gerado automaticamente)
├── templates/
│   └── index.html          # Interface principal
└── static/
    ├── style.css
    └── app.js
```

## Instalação e execução

```bash
# 1. Clone / entre na pasta
cd "D:\Programação\Projetos\Pytube"

# 2. (Opcional mas recomendado) Criar ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Rodar
python app.py
```

Abra **http://127.0.0.1:5000** no navegador.

---

## Formatos disponíveis

| Formato | Tipo  | Requer FFmpeg?   | Descrição                                           |
|---------|-------|-----------------|-----------------------------------------------------|
| MP4     | Vídeo | Sim (>720p)      | Mais compatível. Até 720p: sem FFmpeg.              |
| WebM    | Vídeo | Sim (>720p)      | Formato aberto. Até 720p: sem FFmpeg.               |
| MP3     | Áudio | Não              | Áudio extraído e renomeado para .mp3.               |
| M4A     | Áudio | Não              | Áudio nativo do YouTube, sem conversão.             |

> **Por que qualidades acima de 720p precisam do FFmpeg?**
> O YouTube distribui vídeo e áudio como arquivos separados para resoluções HD (1080p, 1440p, 4K). O FFmpeg é usado para mesclá-los em um único arquivo.

---

## FFmpeg (para downloads em HD)

### Windows
```
winget install ffmpeg
```
ou baixe em https://ffmpeg.org/download.html e adicione ao PATH.

### Linux
```bash
sudo apt install ffmpeg        # Debian/Ubuntu
sudo dnf install ffmpeg        # Fedora
```

### macOS
```bash
brew install ffmpeg
```

Após instalar, reinicie o servidor (`python app.py`). As qualidades acima de 720p serão desbloqueadas automaticamente.

---

## Logs

Os logs ficam em `logs/app.log` e são rotativos (máximo 5 MB por arquivo, 3 arquivos).

Exemplo de saída:
```
[2026-02-28 16:00:00] INFO     Servidor iniciado. FFmpeg disponível: True
[2026-02-28 16:00:05] INFO     POST /api/info — url=https://youtube.com/watch?v=...
[2026-02-28 16:00:07] INFO     Streams encontradas — mp4:9 webm:4 mp3:4 m4a:3
[2026-02-28 16:00:12] INFO     GET /api/download — format=mp4 itag=22
[2026-02-28 16:00:45] INFO     Enviando arquivo 'Titulo do Video.mp4' (mp4)
```

---

## Como atualizar o pytubefix

O `pytubefix` é atualizado frequentemente para acompanhar mudanças na API do YouTube.

```bash
# Ver versão atual
pip show pytubefix

# Atualizar para a versão mais recente
pip install --upgrade pytubefix

# Ou fixar uma versão específica (edite requirements.txt):
# pytubefix==8.x.x
pip install -r requirements.txt
```

### Quando atualizar?
- Downloads começam a falhar com erros como `HTTP Error 403` ou `RegexMatchError`
- O YouTube faz mudanças na forma de autenticação (comum a cada 1–3 meses)
- Uma nova versão com correções foi lançada (veja o [changelog no GitHub](https://github.com/JuanBindez/pytubefix/releases))

### Verificar se precisa atualizar
```bash
pip index versions pytubefix    # lista versões disponíveis
```

---

## Deploy no Vercel

> **Atenção:** o Vercel usa funções serverless com timeout de **60 segundos** (plano Pro) ou **10 segundos** (plano gratuito). Downloads de vídeos grandes podem ultrapassar esse limite. Para uso contínuo, prefira [Railway](https://railway.app) ou [Render](https://render.com).

### 1. Instalar o Vercel CLI

```bash
npm install -g vercel
```

### 2. Criar `vercel.json` na raiz do projeto

```json
{
  "version": 2,
  "builds": [
    { "src": "app.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "app.py" }
  ]
}
```

### 3. Adaptar `app.py` para serverless

O Vercel exige que o objeto Flask se chame `app` (já é o caso). Remova o bloco `if __name__ == "__main__"` ou mantenha-o com `debug=False`:

```python
if __name__ == "__main__":
    app.run(debug=False)
```

### 4. Fazer o deploy

```bash
vercel          # deploy de preview
vercel --prod   # deploy de produção
```

### Limitações no Vercel

| Recurso            | Limitação                                    |
|--------------------|----------------------------------------------|
| Timeout (gratuito) | 10 segundos — vídeos >5 MB vão falhar        |
| Timeout (Pro)      | 60 segundos — vídeos curtos ok               |
| Armazenamento temp | `/tmp` com 512 MB                            |
| FFmpeg             | **Não disponível** — apenas downloads ≤720p  |

Para contornar o timeout, seria necessário usar streaming de dados diretamente do YouTube para o cliente, sem salvar arquivo antes — o que exigiria uma refatoração do endpoint `/api/download`.

### Alternativas recomendadas para produção

| Plataforma    | Características                            |
|---------------|--------------------------------------------|
| **Railway**   | Container completo, sem timeout, FFmpeg OK |
| **Render**    | Deploy simples, plano gratuito lento       |
| **Fly.io**    | Container, baixa latência, gratuito        |
| **VPS/Cloud** | Controle total, deploy via gunicorn        |

#### Exemplo com Railway

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login e deploy
railway login
railway init
railway up
```
