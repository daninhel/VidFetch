import { VercelRequest, VercelResponse } from '@vercel/node';
import { validateYoutubeUrl, handleYoutubeError } from '../src/utils/validation.util';
import { YouTubeService } from '../src/services/youtube.service';

export default async function handler(req: VercelRequest, res: VercelResponse) {
    // CORS Setup
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
    res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    const rawUrl = req.query.url;
    const rawItag = req.query.itag;
    const url = Array.isArray(rawUrl) ? rawUrl[0] : rawUrl;
    const itag = Array.isArray(rawItag) ? rawItag[0] : rawItag;

    if (typeof url !== 'string' || typeof itag !== 'string') {
        return res.status(400).json({ error: 'Parâmetros inválidos ou malformados.' });
    }

    const validation = validateYoutubeUrl(url);
    if (!validation.isValid) {
        return res.status(400).json({ error: validation.error });
    }

    if (!itag || isNaN(Number(itag))) {
        return res.status(400).json({ error: 'ID de stream inválido (itag ausente ou malformado).' });
    }

    try {
        const ytService = new YouTubeService();
        const { directUrl, format, cleanTitle, hasAudio, hasVideo, mimeType } = await ytService.getStreamInfoByItag(url, Number(itag));

        let fileExtension = 'mp4';
        let contentType = 'video/mp4';

        if (hasAudio && !hasVideo) {
            contentType = mimeType || 'audio/mpeg';
            fileExtension = contentType.includes('webm') ? 'mp3' : 'm4a';
        } else {
            contentType = mimeType || 'video/mp4';
            fileExtension = contentType.includes('webm') ? 'webm' : 'mp4';
        }

        res.setHeader('Content-Disposition', `attachment; filename="${encodeURIComponent(cleanTitle)}.${fileExtension}"`);
        res.setHeader('Content-Type', contentType);

        const https = require('https');
        https.get(directUrl, (stream: any) => {
            stream.on('error', (err: any) => {
                console.error('HTTPS Stream Error:', err);
                if (!res.headersSent) {
                    return res.status(500).json({ error: 'Erro no stream do youtube', details: err.message });
                }
                res.end();
            });
            stream.pipe(res);
        }).on('error', (err: any) => {
            console.error('Request Error:', err);
            if (!res.headersSent) {
                return res.status(500).json({ error: 'Erro ao conectar com servidor do youtube', details: err.message });
            }
            res.end();
        });

    } catch (error: any) {
        console.error('Download API Error:', error);
        if (!res.headersSent) {
            const { status, message, suggestion, isAuthError } = handleYoutubeError(error);
            const responseData: any = { error: message, details: error.message };
            if (suggestion) responseData.suggestion = suggestion;
            if (isAuthError) responseData.isAuthError = true;
            return res.status(status).json(responseData);
        }
        res.end();
    }
}
