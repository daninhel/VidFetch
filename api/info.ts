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

    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method Not Allowed' });
    }

    const { url } = req.body || {};

    if (typeof url !== 'string') {
        return res.status(400).json({ error: 'A URL inserida deve ser um formato de texto válido.' });
    }

    const validation = validateYoutubeUrl(url);
    if (!validation.isValid) {
        return res.status(400).json({ error: validation.error });
    }

    try {
        const ytService = new YouTubeService();
        const data = await ytService.getVideoFormats(url);

        return res.status(200).json(data);
    } catch (error: any) {
        console.error('Info API Error:', error);
        const { status, message, suggestion, isAuthError } = handleYoutubeError(error);

        const responseData: any = { error: message, details: error.message };
        if (suggestion) responseData.suggestion = suggestion;
        if (isAuthError) responseData.isAuthError = true;

        return res.status(status).json(responseData);
    }
}
