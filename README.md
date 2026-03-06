# VidFetch (Antigo Pytube)
**Baixador ágil e minimalista de Vídeos e Áudios do YouTube — Otimizado para Vercel Serverless**

O **VidFetch** é um Web App focado em oferecer downloads limpos, rápidos e em múltiplas qualidades (MP4, MP3, WebM e M4A) utilizando uma arquitetura 100% *Serverless* e moderna, driblando as restrições robóticas do Google/YouTube sem sobrecarregar seu disco rígido ou memória RAM. 

## 🚀 Arquitetura e Tecnologias
O projeto foi totalmente migrado de Python (Flask) para **Node.js (TypeScript)** visando o ecossistema Vercel. 
- **Back-end Serverless:** Construído sobre as Vercel API Routes (`/api/...`). Código roda localmente via `vercel dev` em funções assíncronas isoladas.
- **Engine Core:** `youtube-dl-exec` invocando o poderoso `yt-dlp` por debaixo dos panos para quebrar os desafios de Cipher/poToken avançados que assombram o Node.js.
- **Front-end:** HTML Vanilla, CSS flexível e modular, Javascript nativo com interatividade assíncrona.
- **Proxy Stream:** O backend nunca salva o arquivo! Ele gera a URL do Google, repassa como proxy HTTP direto pro browser através de um `stream.pipe()`, tornando o download escalável.

## 📂 Estrutura de Pastas

```text
/
├── api/                           # [Vercel Serverless API]
│   ├── download.ts                # Endpoint GET que repassa o arquivo para anexar.
│   └── info.ts                    # Endpoint POST que retorna o parse de dados limpos.
├── public/                        # [Frontend Estático]
│   ├── app.js                     # Controla UI, fetch assíncrono, badges e progresso.
│   ├── index.html                 # Ponto de entrada amigável com SEO e Google Adsense.
│   └── style.css                  # Folhas de estilo Vanilla, Glassmorphism, UI fluida.
├── src/                           # [Core Logic e Services]
│   ├── services/
│   │   └── youtube.service.ts     # Invocação do `youtube-dl-exec`, parse e mappings JSON.
│   └── utils/                     
│       └── validation.util.ts     # Regex de YT e parser de mensagens de erros nativos.
├── tests/                         # Sandbox isolada e local para debuggar a extração de API.
├── agent.md                       # Log avançado com os maiores limites do Vercel+YouTube.
├── package.json                   # Dependências NPM e script 'npm start' > 'vercel dev'.
└── vercel.json                    # Redirects de Build limpo na Vercel e definições Serverless.
```

## 🛠 Como Executar Localmente
O Vercel CLI orquestra automaticamente as funções `/api` paralelamente à pasta `/public`.
*Certifique-se de que o FFmpeg e o Node.js v18+ estão instalados globalmente, o yt-dlp pode exigi-lo em algumas extrações!*

1. **Instale os pacotes e dependências globais:**
```bash
npm install -g vercel
npm install
```
2. **Inicie o servidor dev:**
```bash
npm start
```
3. A porta `3000` (ou subsequente) abrirá confirmando a simulação serverless! Acesse e teste a aplicação na interface minimalista web.

## ⚠️ Limitações Conhecidas (Servidor)
- As instâncias da Vercel no plano "Hobby" derrubam processos acima de **10 segundos** (Timeouts). Por esse motivo, FFmpeg de junção de Streams de altíssima definição (1080p, 4K) deve ser tratado com extremo cuidado (o aplicativo hoje esconde flags de 1080p nativamente para evitar travamentos ou as ignora e prioriza `18-360p` ou audios).
- Qualquer modificação de engine profunda *sempre* recorra aos Ciphers confiáveis nativos e de linha de comando (`yt-dlp`), evite bibliotecas empacotadas de JavaScript (`ytdl-core`), o YouTube as barra em horas!
