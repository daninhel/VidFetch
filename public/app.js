(() => {
    'use strict';

    // ── Elements ──────────────────────────────────────────────────────────────
    const urlInput = document.getElementById('url-input');
    const fetchBtn = document.getElementById('fetch-btn');
    const pasteBtn = document.getElementById('paste-btn');
    const loadingEl = document.getElementById('loading');
    const errorBox = document.getElementById('error-box');
    const errorTitle = document.getElementById('error-title');
    const errorMsg = document.getElementById('error-msg');
    const resultSection = document.getElementById('result-section');
    const thumbnail = document.getElementById('thumbnail');
    const videoTitle = document.getElementById('video-title');
    const videoAuthor = document.getElementById('video-author');
    const videoDuration = document.getElementById('video-duration');
    const ffmpegNotice = document.getElementById('ffmpeg-notice');
    const formatTabs = document.getElementById('format-tabs');
    const formatDesc = document.getElementById('format-desc');
    const qualityList = document.getElementById('quality-list');
    const downloadBtn = document.getElementById('download-btn');
    const downloadBtnTx = document.getElementById('download-btn-text');
    const downloadOverl = document.getElementById('download-overlay');

    // ── State ─────────────────────────────────────────────────────────────────
    let videoData = null;
    let currentFormat = 'mp4';
    let selectedItag = null;
    let ffmpegOk = false;
    let downloadTimer = null;

    const FORMAT_DESC = {
        mp4: '🎬 Vídeo com áudio — compatível com todos os dispositivos.',
        webm: '🎬 Vídeo com áudio — formato aberto, ideal para web.',
        mp3: '🎵 Somente áudio — ideal para músicas e podcasts.',
        m4a: '🎵 Áudio nativo do YouTube — alta qualidade, sem conversão.',
    };

    const ERROR_TITLES = {
        400: '⚠️ Link inválido',
        403: '⛔ Acesso negado',
        404: '🔍 Não encontrado',
        503: '🌐 Erro de conexão',
        500: '💥 Erro no servidor',
    };

    // ── Helpers ───────────────────────────────────────────────────────────────

    function formatSeconds(sec) {
        if (!sec) return '';
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = sec % 60;
        if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        return `${m}:${String(s).padStart(2, '0')}`;
    }

    /** Erro de BUSCA — esconde resultado */
    function showFetchError(msg, status = 500) {
        errorTitle.textContent = ERROR_TITLES[status] || '❌ Erro';
        errorMsg.textContent = msg;
        errorBox.classList.remove('hidden');
        resultSection.classList.add('hidden');
    }

    /** Erro de DOWNLOAD — mantém resultado visível */
    function showDownloadError(msg, status = 500) {
        errorTitle.textContent = `${(ERROR_TITLES[status] || '❌ Erro')} — Falha no download`;
        errorMsg.textContent = msg;
        errorBox.classList.remove('hidden');
    }

    function hideError() { errorBox.classList.add('hidden'); }

    function setLoading(on) {
        loadingEl.classList.toggle('hidden', !on);
        fetchBtn.disabled = on || !urlInput.value.trim();
    }

    function setDownloadLoading(on) {
        downloadBtn.disabled = on;
        if (on) {
            downloadBtnTx.textContent = 'Iniciando...';
            downloadOverl.classList.remove('hidden');
        } else {
            updateDownloadBtn();
            downloadOverl.classList.add('hidden');
            if (downloadTimer) { clearTimeout(downloadTimer); downloadTimer = null; }
        }
    }

    // ── URL input ─────────────────────────────────────────────────────────────

    urlInput.addEventListener('input', () => {
        fetchBtn.disabled = !urlInput.value.trim();
        hideError();
    });

    urlInput.addEventListener('keydown', e => {
        if (e.key === 'Enter') fetchVideo();
    });

    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            urlInput.value = text.trim();
            urlInput.dispatchEvent(new Event('input'));
        } catch {
            urlInput.focus();
        }
    });

    // ── Fetch video info ──────────────────────────────────────────────────────

    fetchBtn.addEventListener('click', fetchVideo);

    async function fetchVideo() {
        const url = urlInput.value.trim();
        if (!url) return;

        hideError();
        resultSection.classList.add('hidden');
        setLoading(true);

        try {
            const res = await fetch('/api/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });
            const data = await res.json();

            if (!res.ok || data.error) {
                showFetchError(data.error || 'Erro ao buscar o vídeo.', res.status);
                return;
            }

            videoData = data;
            ffmpegOk = !!data.ffmpeg;
            renderVideoInfo();
            switchTab('mp4');
            hideError();
            resultSection.classList.remove('hidden');

        } catch {
            showFetchError(
                navigator.onLine
                    ? 'Não foi possível conectar ao servidor. Tente novamente em instantes.'
                    : 'Sem conexão com a internet. Verifique sua rede e tente novamente.',
                503,
            );
        } finally {
            setLoading(false);
        }
    }

    // ── Render video metadata ─────────────────────────────────────────────────

    function renderVideoInfo() {
        thumbnail.src = videoData.thumbnail || '';
        thumbnail.alt = `Miniatura: ${videoData.title}`;
        videoTitle.textContent = videoData.title || 'Sem título';
        videoAuthor.textContent = videoData.author || '';
        const dur = formatSeconds(videoData.duration);
        videoDuration.textContent = dur ? `⏱ ${dur}` : '';
        ffmpegNotice.classList.toggle('hidden', ffmpegOk);
    }

    // ── Tabs ──────────────────────────────────────────────────────────────────

    formatTabs.addEventListener('click', e => {
        const tab = e.target.closest('.tab');
        if (!tab) return;
        const fmt = tab.dataset.format;
        if (fmt === currentFormat) return;
        switchTab(fmt);
        hideError();
    });

    function switchTab(fmt) {
        document.querySelectorAll('.tab').forEach(t => {
            const active = t.dataset.format === fmt;
            t.classList.toggle('active', active);
            t.setAttribute('aria-selected', String(active));
        });
        currentFormat = fmt;
        selectedItag = null;
        formatDesc.textContent = FORMAT_DESC[fmt] || '';
        updateDownloadBtn();
        renderQualities(fmt);
    }

    // ── Render quality options ────────────────────────────────────────────────

    function renderQualities(fmt) {
        qualityList.innerHTML = '';
        const streams = videoData?.formats?.[fmt] || [];

        if (!streams.length) {
            qualityList.innerHTML = '<p class="no-streams">Nenhuma opção disponível para este formato.</p>';
            return;
        }

        let firstAvailable = null;

        streams.forEach(stream => {
            const item = document.createElement('label');
            item.className = 'quality-item';
            item.htmlFor = `q-${stream.itag}`;

            const radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = 'quality';
            radio.value = stream.itag;
            radio.id = `q-${stream.itag}`;
            radio.disabled = !stream.available;

            if (firstAvailable === null && stream.available) {
                firstAvailable = stream;
                radio.checked = true;
                selectedItag = String(stream.itag);
            }

            radio.addEventListener('change', () => {
                selectedItag = String(stream.itag);
                hideError();
                updateDownloadBtn();
            });

            let badge;
            if (['mp3', 'm4a'].includes(fmt)) badge = 'Áudio';
            else if (stream.progressive) badge = 'V+A ✓';
            else badge = 'Ext.';

            const labelEl = document.createElement('span');
            labelEl.className = `quality-label${!stream.available ? ' disabled' : ''}`;
            labelEl.innerHTML = `<strong>${stream.quality}</strong><span class="q-badge">${badge}</span>`;

            item.appendChild(radio);
            item.appendChild(labelEl);
            qualityList.appendChild(item);
        });

        updateDownloadBtn();
    }

    // ── Download button state ─────────────────────────────────────────────────

    function updateDownloadBtn() {
        if (selectedItag) {
            downloadBtn.disabled = false;
            downloadBtnTx.textContent = `Baixar ${currentFormat.toUpperCase()}`;
        } else {
            downloadBtn.disabled = true;
            downloadBtnTx.textContent = 'Selecione uma qualidade';
        }
    }

    // ── Download ──────────────────────────────────────────────────────────────
    // Uma única request via anchor nativo — sem double-request HEAD+GET que
    // triggerava BotDetection do YouTube (pytubefix sendo instanciado 2x).

    downloadBtn.addEventListener('click', () => {
        if (!selectedItag || !videoData) return;

        const url = urlInput.value.trim();
        const params = new URLSearchParams({ url, itag: selectedItag, format: currentFormat });
        const dlUrl = `/api/download?${params}`;

        hideError();
        setDownloadLoading(true);

        // Navegação nativa: browser faz o streaming sem bufferizar em memória
        const fileTitle = (videoData.safe_title || 'video').replace(/\s+/g, '_');
        const a = document.createElement('a');
        a.href = dlUrl;
        a.download = `${fileTitle}.${currentFormat}`;   // ex: Titulo_do_Video.mp4
        a.rel = 'noopener noreferrer';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        // Esconde o overlay após 3s (download já está no gerenciador do browser)
        downloadTimer = setTimeout(() => setDownloadLoading(false), 3000);
    });

})();
